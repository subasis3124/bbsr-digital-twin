import os
import argparse
import datetime
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import mlflow
from sqlalchemy.orm import Session
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from backend.app.database import SessionLocal
from backend.app.models import Traffic, GNNTrafficPrediction, Road
from ml.gnn_feature_extractor import GNNFeatureExtractor, SpatiotemporalSplitter
from ml.gnn_models import GNNTrafficForecaster
from ml.traffic_models import NaiveForecaster, HistoricalAverageForecaster, calculate_metrics

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def setup_mlflow():
    tracking_uri = "sqlite:////tmp/mlflow_bbsr.db"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("Bhubaneswar_GNN_Traffic_Forecasting")
    print(f"MLflow configured with tracking database: {tracking_uri}")

def train_and_evaluate_gnn(args):
    set_seed(args.seed)
    db: Session = SessionLocal()
    
    try:
        obs_count = db.query(Traffic).count()
        if obs_count == 0:
            raise ValueError("No traffic observations found in database. Run ETL pipeline first.")
            
        print(f"Loaded {obs_count} traffic observations from database.")
        
        # 1. Feature Extraction & Graph Construction
        extractor = GNNFeatureExtractor(db)
        graph_data, snapshots = extractor.extract_spatiotemporal_dataset()
        
        if not snapshots:
            print("Snapshot sequence is empty. Ensure sufficient chronological data.")
            return

        stats = graph_data["statistics"]
        num_nodes = graph_data["num_nodes"]
        edge_index = graph_data["edge_index"]
        road_to_idx = graph_data["road_to_idx"]
        idx_to_road = graph_data["idx_to_road"]

        print(f"Graph Topology Built: Nodes={stats['num_nodes']}, Edges={stats['num_edges']}, "
              f"Components={stats['num_connected_components']}, Isolated={stats['num_isolated_nodes']}")

        # 2. Spatiotemporal Chronological Split
        train_snaps, val_snaps, test_snaps = SpatiotemporalSplitter.split(snapshots)
        print(f"Dataset Partitioned: Train={len(train_snaps)}, Val={len(val_snaps)}, Test={len(test_snaps)}")

        # Check synthetic status
        is_synthetic = (db.query(Traffic).filter(Traffic.source == "synthetic_simulator").count() > 0)
        data_provenance = "synthetic_fallback" if is_synthetic else "validated_model"

        if is_synthetic and not args.allow_synthetic:
            print("BLOCKER: Synthetic observations detected, but --allow-synthetic flag was not passed.")
            print("Run with: python ml/gnn_train.py --allow-synthetic")
            return

        # 3. Fit & Evaluate Baselines on Test Snapshots
        # Flatten test snapshots for baseline evaluation
        y_test_all, y_naive_all, y_hist_all = [], [], []
        X_test_tabular, y_test_tabular = [], []
        X_train_tabular, y_train_tabular = [], []

        for s in train_snaps:
            X_snap = s["X"].numpy()
            y_snap = s["y"].numpy().squeeze()
            mask = s["mask"].numpy()
            X_train_tabular.append(X_snap[mask])
            y_train_tabular.append(y_snap[mask])

        for s in test_snaps:
            X_snap = s["X"].numpy()
            y_snap = s["y"].numpy().squeeze()
            mask = s["mask"].numpy()
            
            # Naive baseline uses lag_1h (index 6 in features)
            lag_1h = X_snap[:, 6]
            y_test_all.extend(y_snap[mask])
            y_naive_all.extend(lag_1h[mask])
            
            X_test_tabular.append(X_snap[mask])
            y_test_tabular.append(y_snap[mask])

        y_test_arr = np.array(y_test_all)
        y_naive_arr = np.array(y_naive_all)

        metrics_naive = calculate_metrics(y_test_arr, y_naive_arr)
        print(f"\n--- Baseline 1 (Naive Last Observed) Metrics: {metrics_naive}")

        # Baseline 2: XGBoost Regressor on tabular node features
        X_tr = np.vstack(X_train_tabular) if X_train_tabular else np.empty((0, 14))
        y_tr = np.concatenate(y_train_tabular) if y_train_tabular else np.empty((0,))
        X_te = np.vstack(X_test_tabular) if X_test_tabular else np.empty((0, 14))
        y_te = np.concatenate(y_test_tabular) if y_test_tabular else np.empty((0,))

        metrics_xgb = {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0}
        if len(X_tr) > 0 and len(X_te) > 0:
            xgb_model = xgb.XGBRegressor(n_estimators=50, max_depth=5, random_state=args.seed)
            xgb_model.fit(X_tr, y_tr)
            preds_xgb = xgb_model.predict(X_te)
            metrics_xgb = calculate_metrics(y_te, preds_xgb)
            print(f"--- Baseline 2 (XGBoost Regressor) Metrics: {metrics_xgb}")

        # 4. GNN Model Training
        in_channels = train_snaps[0]["X"].size(1)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Training GNN on device: {device} using architecture: {args.architecture}")

        gnn_model = GNNTrafficForecaster(
            architecture=args.architecture,
            in_channels=in_channels,
            hidden_channels=args.hidden_dim,
            out_channels=1,
            num_layers=args.num_layers,
            dropout=0.1
        ).to(device)

        edge_index_dev = edge_index.to(device)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(gnn_model.parameters(), lr=args.lr, weight_decay=1e-4)

        best_val_loss = float("inf")
        best_model_state = None

        for epoch in range(1, args.epochs + 1):
            gnn_model.train()
            total_train_loss = 0.0
            
            for snap in train_snaps:
                x_in = snap["X"].to(device)
                y_in = snap["y"].to(device)
                mask_in = snap["mask"].to(device)

                optimizer.zero_grad()
                pred = gnn_model(x_in, edge_index_dev)
                loss = criterion(pred[mask_in], y_in[mask_in])
                loss.backward()
                optimizer.step()

                total_train_loss += loss.item()

            avg_train_loss = total_train_loss / max(1, len(train_snaps))

            # Validation
            gnn_model.eval()
            total_val_loss = 0.0
            with torch.no_grad():
                for snap in val_snaps:
                    x_in = snap["X"].to(device)
                    y_in = snap["y"].to(device)
                    mask_in = snap["mask"].to(device)
                    pred = gnn_model(x_in, edge_index_dev)
                    val_loss = criterion(pred[mask_in], y_in[mask_in])
                    total_val_loss += val_loss.item()

            avg_val_loss = total_val_loss / max(1, len(val_snaps))

            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_model_state = gnn_model.state_dict().copy()

            if epoch % 10 == 0 or epoch == args.epochs:
                print(f"Epoch [{epoch:02d}/{args.epochs:02d}] - Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

        # Load best checkpoint
        if best_model_state is not None:
            gnn_model.load_state_dict(best_model_state)

        # Save model weights to disk
        os.makedirs("models", exist_ok=True)
        model_path = "models/gnn_traffic_model.pt"
        torch.save({
            "model_state": gnn_model.state_dict(),
            "architecture": args.architecture,
            "in_channels": in_channels,
            "hidden_channels": args.hidden_dim,
            "num_layers": args.num_layers,
            "statistics": stats
        }, model_path)
        print(f"Saved GNN model checkpoint to {model_path}")

        # 5. Evaluate GNN on Test Snapshots
        gnn_model.eval()
        gnn_test_preds, gnn_test_targets = [], []

        with torch.no_grad():
            for snap in test_snaps:
                x_in = snap["X"].to(device)
                y_in = snap["y"].numpy().squeeze()
                mask_in = snap["mask"].numpy()
                pred = gnn_model(x_in, edge_index_dev).cpu().numpy().squeeze()

                gnn_test_preds.extend(pred[mask_in])
                gnn_test_targets.extend(y_in[mask_in])

        metrics_gnn = calculate_metrics(np.array(gnn_test_targets), np.array(gnn_test_preds))
        print(f"\n==========================================")
        print(f"GNN ({args.architecture}) Test Metrics: {metrics_gnn}")
        print(f"Naive Baseline Test Metrics: {metrics_naive}")
        print(f"XGBoost Baseline Test Metrics: {metrics_xgb}")
        print(f"==========================================\n")

        # 6. MLflow Integration
        setup_mlflow()
        run_name = f"gnn_{args.architecture.lower()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params({
                "model_type": "GNN",
                "architecture": args.architecture,
                "hidden_channels": args.hidden_dim,
                "num_layers": args.num_layers,
                "lr": args.lr,
                "epochs": args.epochs,
                "seed": args.seed,
                "num_nodes": stats["num_nodes"],
                "num_edges": stats["num_edges"],
                "is_synthetic": is_synthetic,
                "data_provenance": data_provenance
            })
            
            mlflow.log_metrics({
                "gnn_test_mae": metrics_gnn["MAE"],
                "gnn_test_rmse": metrics_gnn["RMSE"],
                "gnn_test_r2": metrics_gnn["R2"],
                "naive_test_mae": metrics_naive["MAE"],
                "xgb_test_mae": metrics_xgb["MAE"]
            })
            
            mlflow.log_artifact(model_path)
            print("Logged GNN metrics and model artifact to MLflow repository.")

        # 7. Prediction Generation & DB Storage
        latest_snap = snapshots[-1]
        latest_ts = latest_snap["timestamp"]
        future_ts = latest_ts + pd.Timedelta(hours=1)

        gnn_model.eval()
        with torch.no_grad():
            x_latest = latest_snap["X"].to(device)
            future_preds = gnn_model(x_latest, edge_index_dev).cpu().numpy().squeeze()

        # Clear previous GNN predictions
        db.query(GNNTrafficPrediction).delete()
        db.commit()

        predictions_to_insert = []
        for idx in range(num_nodes):
            rid = idx_to_road[idx]
            pred_speed = float(future_preds[idx]) if num_nodes > 1 else float(future_preds)
            
            # Simple congestion mapping
            road_obj = db.query(Road).filter(Road.id == rid).first()
            maxspeed = float(road_obj.maxspeed) if road_obj and road_obj.maxspeed else 40.0
            congestion = max(0.0, min(1.0, 1.0 - (pred_speed / maxspeed)))

            predictions_to_insert.append(GNNTrafficPrediction(
                road_id=rid,
                prediction_time=future_ts.to_pydatetime(),
                forecast_horizon_minutes=60,
                predicted_speed=pred_speed,
                predicted_congestion_ratio=congestion,
                gnn_architecture=args.architecture,
                model_name=f"GNN_{args.architecture}",
                model_version="1.0.0",
                is_synthetic=is_synthetic,
                data_provenance_status=data_provenance
            ))

        db.bulk_save_objects(predictions_to_insert)
        db.commit()
        print(f"Persisted {len(predictions_to_insert)} GNN forecasts into database gnn_traffic_predictions table.")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - Phase 10 GNN Training Pipeline")
    parser.add_argument("--architecture", type=str, default="GraphSAGE", choices=["GraphSAGE", "GCN", "GAT"], help="GNN Architecture")
    parser.add_argument("--hidden-dim", type=int, default=64, help="Hidden dimension size")
    parser.add_argument("--num-layers", type=int, default=2, help="Number of graph conv layers")
    parser.add_argument("--lr", type=float, default=0.005, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--allow-synthetic", action="store_true", help="Allow synthetic observations")
    
    args = parser.parse_args()
    train_and_evaluate_gnn(args)
