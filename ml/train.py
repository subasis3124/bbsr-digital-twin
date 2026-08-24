import os
import argparse
import logging
import json
import joblib
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
import xgboost as xgb
import mlflow
import shap

from backend.app.database import SessionLocal
from backend.app.models import FloodEvent, Prediction
from ml.feature_extractor import FeatureExtractor
from ml.spatial_cv import SpatialBlockSplitter

# Configure ML Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ML.Train")

# Set local SQLite Tracking URI in native Linux path to bypass WSL NTFS file-mount locking bugs
mlflow.set_tracking_uri("sqlite:////tmp/mlflow_bbsr.db")
mlflow.set_experiment("BBSR_Flood_Susceptibility")

def get_target_labels() -> pd.DataFrame:
    """
    Checks which cell centroids intersect with historical flood polygons in PostGIS.
    """
    db = SessionLocal()
    query = """
        SELECT 
            c.id as cell_id,
            EXISTS(
                SELECT 1 FROM flood_events f 
                WHERE ST_Intersects(f.geom, c.centroid)
            ) as target
        FROM spatial_grid_cells c
    """
    try:
        results = db.execute(text_query(query)).fetchall()
        df = pd.DataFrame(results, columns=["cell_id", "target"])
        df["target"] = df["target"].astype(int)
        return df
    except Exception as e:
        logger.error(f"Failed to query target labels: {e}")
        raise
    finally:
        db.close()

def text_query(q):
    from sqlalchemy import text
    return text(q)

def train_pipeline(allow_synthetic: bool = False):
    """
    Main training pipeline.
    """
    logger.info("Initializing Flood Risk ML Training Pipeline...")
    
    # 1. Spatial Features
    extractor = FeatureExtractor()
    try:
        df_features = extractor.extract_features()
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")
        return
        
    if df_features.empty:
        logger.error("No features extracted. Ingestion state might be empty.")
        return
        
    # 2. Extract Targeted labels from flood_events
    df_targets = get_target_labels()
    df_data = pd.merge(df_features, df_targets, on="cell_id")
    
    total_positives = df_data["target"].sum()
    logger.info(f"Target distribution check: Total Cells={len(df_data)}, Positive (Flooded) Labels={total_positives}")
    
    if total_positives == 0:
        if allow_synthetic:
            logger.warning("No real flood observations present in database. Generating synthetic tags (target=1 if elevation < 25m and NDVI < 0.45) ONLY for pipeline evaluation.")
            # Synthesize highly spatial, correlated dummy label for structural testing
            df_data["target"] = ((df_data["elevation"] < 25.0) & (df_data["ndvi"] < 0.45)).astype(int)
            total_positives = df_data["target"].sum()
            logger.warning(f"Generated {total_positives} synthetic positive labels.")
        else:
            block_msg = "Model training is blocked because a defensible flood target dataset is not currently available."
            logger.error(block_msg)
            print(f"\n[SCIENTIFIC BLOCK] {block_msg}\n")
            return
            
    # Define features
    feature_cols = [
        "elevation", "slope", "ndvi", "ndwi", "ndbi", 
        "population_count", "dist_to_water", "dist_to_road", "dist_to_building"
    ]
    
    X = df_data[feature_cols]
    y = df_data["target"]
    
    # Calculate scale factors for class imbalance
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    pos_weight = float(n_neg / n_pos) if n_pos > 0 else 1.0
    logger.info(f"Imbalance analysis: Neg={n_neg}, Pos={n_pos}, ClassRatio={pos_weight:.2f}")
    
    # 3. Spatial Cross-Validation Groups
    splitter = SpatialBlockSplitter(block_size_degrees=0.02, n_splits=5)
    splits = list(splitter.split(df_data, x_col="lon", y_col="lat", label_col="target"))
    
    # 4. Train Models
    models = {
        "baseline": DummyClassifier(strategy="most_frequent"),
        "random_forest": RandomForestClassifier(
            n_estimators=100, 
            max_depth=8, 
            class_weight="balanced", 
            random_state=42
        ),
        "xgboost": xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            scale_pos_weight=pos_weight,
            random_state=42,
            eval_metric="logloss"
        )
    }
    
    best_model_name = None
    best_model_score = -1.0
    best_model = None
    best_model_shap_values = None
    
    for name, model in models.items():
        logger.info(f"Evaluating {name} model with Spatial Block CV...")
        fold_metrics = {"precision": [], "recall": [], "f1": [], "roc_auc": []}
        
        for fold, (train_idx, val_idx) in enumerate(splits):
            X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
            X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
            
            # Skip folds if they lack both classes and aren't baselines
            if len(y_train.unique()) < 2 or len(y_val.unique()) < 2:
                if name != "baseline":
                    continue
                    
            model.fit(X_train, y_train)
            
            # Predict
            preds = model.predict(X_val)
            probs = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else preds
            
            fold_metrics["precision"].append(precision_score(y_val, preds, zero_division=0))
            fold_metrics["recall"].append(recall_score(y_val, preds, zero_division=0))
            fold_metrics["f1"].append(f1_score(y_val, preds, zero_division=0))
            try:
                fold_metrics["roc_auc"].append(roc_auc_score(y_val, probs))
            except ValueError:
                fold_metrics["roc_auc"].append(0.5)
                
        # Aggregate stats
        agg_metrics = {k: np.mean(v) for k, v in fold_metrics.items()}
        logger.info(f"{name} metrics: "
                    f"F1={agg_metrics['f1']:.4f}, "
                    f"Precision={agg_metrics['precision']:.4f}, "
                    f"Recall={agg_metrics['recall']:.4f}, "
                    f"AUC={agg_metrics['roc_auc']:.4f}")
        
        # Track run with MLflow
        with mlflow.start_run(run_name=f"flood_{name}"):
            # Log params
            if hasattr(model, "get_params"):
                params = model.get_params()
                mlflow.log_params({k: str(v) for k, v in params.items() if len(str(v)) < 250})
            mlflow.log_param("model_type", name)
            mlflow.log_param("features", ",".join(feature_cols))
            
            # Log metrics
            for k, val in agg_metrics.items():
                mlflow.log_metric(f"mean_{k}", val)
            mlflow.log_metric("total_cells", len(df_data))
            mlflow.log_metric("positive_labels", n_pos)
            
            # Fit final model on holding data for artifact generation
            model.fit(X, y)
            
            # Confusion matrix
            y_pred_all = model.predict(X)
            cm = confusion_matrix(y, y_pred_all)
            disp = ConfusionMatrixDisplay(confusion_matrix=cm)
            fig, ax = plt.subplots(figsize=(6, 6))
            disp.plot(ax=ax, cmap="Blues")
            ax.set_title(f"Confusion Matrix - {name}")
            cm_path = f"confusion_matrix_{name}.png"
            plt.savefig(cm_path, bbox_inches="tight")
            plt.close()
            mlflow.log_artifact(cm_path)
            os.remove(cm_path)
            
            # Choose best model (by F1 score)
            if name != "baseline" and agg_metrics["f1"] > best_model_score:
                best_model_score = agg_metrics["f1"]
                best_model_name = name
                best_model = model
                
    # 5. Best Model Explainability & Inference dump
    if best_model:
        logger.info(f"Selected best model: {best_model_name} with F1-Score of {best_model_score:.4f}.")
        
        # Save model locally and to MLflow
        model_filename = "best_flood_model.joblib"
        metadata = {
            "model_name": best_model_name,
            "features": feature_cols,
            "imbalance_ratio": pos_weight,
            "training_time": datetime.now(timezone.utc).isoformat(),
            "f1_score": float(best_model_score)
        }
        
        # Save model + config
        os.makedirs("models", exist_ok=True)
        joblib.dump({"model": best_model, "metadata": metadata}, os.path.join("models", model_filename))
        
        with mlflow.start_run(run_name="flood_best_model_artifacts"):
            mlflow.log_params(metadata)
            mlflow.log_artifact(os.path.join("models", model_filename))
            
            # Log feature importance chart if supported
            if hasattr(best_model, "feature_importances_"):
                importances = best_model.feature_importances_
                indices = np.argsort(importances)[::-1]
                
                plt.figure(figsize=(8, 6))
                plt.title(f"Global Feature Importance - {best_model_name}")
                plt.bar(range(X.shape[1]), importances[indices], align="center")
                plt.xticks(range(X.shape[1]), [feature_cols[i] for i in indices], rotation=45, ha="right")
                plt.tight_layout()
                feat_chart = "feature_importance.png"
                plt.savefig(feat_chart)
                plt.close()
                mlflow.log_artifact(feat_chart)
                os.remove(feat_chart)
                
            # 6. SHAP Explainability on the best model
            logger.info("Computing SHAP values for model explainability...")
            try:
                # Use TreeExplainer for Random Forest / XGBoost
                explainer = shap.TreeExplainer(best_model)
                # Compute on local fraction to reduce computational time
                sub_X = X.sample(n=min(len(X), 1000), random_state=42)
                shap_values = explainer(sub_X)
                
                # Global SHAP Summary Plot
                plt.figure()
                shap.summary_plot(shap_values, sub_X, show=False)
                plt.tight_layout()
                shap_plot_path = "shap_summary_plot.png"
                plt.savefig(shap_plot_path)
                plt.close()
                mlflow.log_artifact(shap_plot_path)
                os.remove(shap_plot_path)
                logger.info("SHAP explainability logs generated successfully.")
                
                # Fetch mean absolute shap dictionary to load into Predictions
                mean_shap = np.abs(shap_values.values).mean(axis=0)
                shap_dict = {feature_cols[i]: float(mean_shap[i]) for i in range(len(feature_cols))}
            except Exception as e:
                logger.warning(f"SHAP trace failed: {e}. Defaulting to dummy features mapping.")
                shap_dict = {f: 0.0 for f in feature_cols}
                
        # 7. Spatial Inferences loading to database predictions table
        logger.info("Saving spatial risk inferences into the predictions table...")
        db = SessionLocal()
        
        # Predict probabilities
        probabilities = best_model.predict_proba(X)[:, 1]
        
        # Load predictions batch
        current_time = datetime.now(timezone.utc)
        
        # Delete existing flood model records to remain idempotent
        db.query(Prediction).filter(Prediction.model_name == "flood_susceptibility").delete()
        db.commit()
        
        batch = []
        for idx, row in df_data.iterrows():
            prob = float(probabilities[idx])
            
            # Map risk classes based on threshold boundaries
            if prob < 0.25:
                risk_class = "LOW"
            elif prob < 0.50:
                risk_class = "MEDIUM"
            elif prob < 0.75:
                risk_class = "HIGH"
            else:
                risk_class = "VERY HIGH"
                
            prediction_record = Prediction(
                cell_id=int(row["cell_id"]),
                model_name="flood_susceptibility",
                model_version="1.0.0",
                prediction_time=current_time,
                predicted_probability=prob,
                predicted_class=risk_class,
                feature_importance_shap=shap_dict
            )
            batch.append(prediction_record)
            
        # Bulk save
        try:
            chunk_size = 1000
            for i in range(0, len(batch), chunk_size):
                db.bulk_save_objects(batch[i:i+chunk_size])
            db.commit()
            logger.info(f"Loaded {len(batch)} spatial grid predictions to database.")
        except Exception as load_err:
            db.rollback()
            logger.error(f"Failed to record risk predictions in PostGIS: {load_err}")
            raise
        finally:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - FloodSusceptibility Model Pipe")
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="If set, runs model logic using synthetic spatial labels as fallback if empty."
    )
    args = parser.parse_args()
    
    train_pipeline(allow_synthetic=args.allow_synthetic)
