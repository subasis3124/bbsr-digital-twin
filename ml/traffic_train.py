import os
import argparse
import datetime
import numpy as np
import pandas as pd
import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import Traffic, TrafficPrediction, Road
from ml.traffic_feature_extractor import TrafficFeatureExtractor
from ml.traffic_splitter import TemporalTrafficSplitter
from ml.traffic_models import NaiveForecaster, HistoricalAverageForecaster, calculate_metrics

def setup_mlflow():
    # Use a native VM SQLite database path to prevent Windows shared filesystem locking issues
    tracking_uri = "sqlite:////tmp/mlflow_bbsr.db"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("Bhubaneswar_Traffic_Forecasting")
    print(f"MLflow configured with tracking database: {tracking_uri}")

def train_and_evaluate(args):
    db: Session = SessionLocal()
    
    try:
        # Check if traffic data exists
        obs_count = db.query(Traffic).count()
        if obs_count == 0:
            raise ValueError("No traffic observations found in the database. Run the ETL flow first: python pipelines/run.py --source traffic")
            
        print(f"Loaded {obs_count} traffic observations from the database.")
        
        # 1. Feature Extraction
        extractor = TrafficFeatureExtractor(db)
        df_roads, df_traffic = extractor.load_raw_data()
        df_features = extractor.extract_features(df_roads, df_traffic)
        
        if df_features.empty:
            print("Feature matrix is empty. Ensure you have sufficient chronological observation spans.")
            return
            
        # 2. Chronological Split
        df_train, df_val, df_test = TemporalTrafficSplitter.split(df_features)
        print(f"Dataset Chronologically Partitioned: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)}")
        
        # Define target and input columns
        # Filter out metadata columns
        exclude_cols = {"id", "timestamp", "road_id", "observed_speed", "congestion_ratio", "source"}
        feature_cols = [col for col in df_features.columns if col not in exclude_cols]
        target_col = "observed_speed"
        
        X_train, y_train = df_train[feature_cols], df_train[target_col].values
        X_val, y_val = df_val[feature_cols], df_val[target_col].values
        X_test, y_test = df_test[feature_cols], df_test[target_col].values
        
        # Determine if data has synthetic characteristics
        is_synthetic = (db.query(Traffic).filter(Traffic.source == "synthetic_simulator").count() > 0)
        data_provenance = "synthetic_fallback" if is_synthetic else "validated_model"
        
        # Check security validation warnings
        if is_synthetic and not args.allow_synthetic:
            print("BLOCKER: Synthetically generated observations detected, but --allow-synthetic was not set.")
            print("To verify models, re-run with: python ml/traffic_train.py --allow-synthetic")
            return
            
        # 3. Fit & Evaluate Estimators
        # -- Baseline 1: Naive (previous value)
        naive = NaiveForecaster()
        naive.fit(X_train, y_train)
        preds_naive = naive.predict(X_test)
        metrics_naive = calculate_metrics(y_test, preds_naive)
        print(f"\nNaive Baseline Metrics: {metrics_naive}")
        
        # -- Baseline 2: Historical Average
        hist_avg = HistoricalAverageForecaster()
        hist_avg.fit(df_train, y_train)
        preds_hist = hist_avg.predict(df_test)
        metrics_hist = calculate_metrics(y_test, preds_hist)
        print(f"Historical Average Metrics: {metrics_hist}")
        
        # -- RandomForest Regressor
        rf = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42)
        rf.fit(X_train, y_train)
        preds_rf = rf.predict(X_test)
        metrics_rf = calculate_metrics(y_test, preds_rf)
        print(f"Random Forest Regressor Metrics: {metrics_rf}")
        
        # -- XGBoost Regressor
        xgb_reg = xgb.XGBRegressor(n_estimators=50, max_depth=6, random_state=42)
        xgb_reg.fit(X_train, y_train)
        preds_xgb = xgb_reg.predict(X_test)
        metrics_xgb = calculate_metrics(y_test, preds_xgb)
        print(f"XGBoost Regressor Metrics: {metrics_xgb}")
        
        # 4. MLflow Logging
        setup_mlflow()
        with mlflow.start_run(run_name=f"traffic_model_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            mlflow.log_params({
                "model_type": "xgboost",
                "n_estimators": 50,
                "max_depth": 6,
                "is_synthetic": is_synthetic,
                "data_provenance": data_provenance,
                "train_records": len(X_train),
                "test_records": len(X_test)
            })
            
            for k, v in metrics_xgb.items():
                mlflow.log_metric(f"test_{k.lower()}", v)
                
            mlflow.xgboost.log_model(xgb_reg, "traffic_xgb_regressor")
            print("Successfully recorded run metrics in MLflow offline repository.")

        # 5. Prediction Generation & DB Storage
        # We forecast 1 hour (60 minutes) into the future from our last timestamp
        last_timestamp = df_features["timestamp"].max()
        future_timestamp = last_timestamp + pd.Timedelta(hours=1)
        
        # We extract features relative to the future timestamp
        # The lag values correspond to the values at last_timestamp (which is fully observed!)
        # We take the latest observed state for each road:
        latest_obs = df_features[df_features["timestamp"] == last_timestamp].copy()
        
        # Create input features for the future forecasting
        future_features = latest_obs.copy()
        future_features["timestamp"] = future_timestamp
        
        # Lags shift chronologically:
        # lag_1h at T+1 becomes the speed at T (last_timestamp)
        future_features["lag_observed_speed_2h"] = latest_obs["lag_observed_speed_1h"]
        future_features["lag_observed_speed_1h"] = latest_obs["observed_speed"]
        
        # Recalculate rolling average based on new lag values:
        # average over [T, T-1h, T-2h]
        future_features["rolling_average_speed_3h"] = (
            latest_obs["observed_speed"] + 
            latest_obs["lag_observed_speed_1h"] + 
            latest_obs["lag_observed_speed_2h"]
        ) / 3.0
        
        # Temporal values for the future timestamp
        future_features["hour"] = future_timestamp.hour
        future_features["day_of_week"] = future_timestamp.dayofweek
        future_features["is_weekend"] = int(future_timestamp.dayofweek >= 5)
        
        # Predict speeds
        X_future = future_features[feature_cols]
        predicted_speeds = xgb_reg.predict(X_future)
        
        # Clear existing predictions before saving new ones to maintain idempotency
        db.query(TrafficPrediction).delete()
        db.commit()
        
        # Save predictions
        forecasts = []
        for idx, row in future_features.reset_index(drop=True).iterrows():
            pred_speed = float(predicted_speeds[idx])
            
            # Simple congestion mapping: ratio increases as predicted speed drops relative to speed limit
            limit = row.get("maxspeed", 40)
            congestion = max(0.0, min(1.0, float(1.0 - (pred_speed / limit))))
            
            forecast = TrafficPrediction(
                road_id=int(row["road_id"]),
                prediction_time=future_timestamp.to_pydatetime(),
                forecast_horizon_minutes=60,
                predicted_speed=pred_speed,
                predicted_congestion_ratio=congestion,
                model_name="xgboost_regressor",
                model_version="1.0.0",
                is_synthetic=is_synthetic,
                data_provenance_status=data_provenance
            )
            forecasts.append(forecast)
            
        db.bulk_save_objects(forecasts)
        db.commit()
        print(f"Stored {len(forecasts)} forecasts for timestamp {future_timestamp} in database traffic_predictions table.")
        
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - Traffic Forecasting Pipeline")
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Explicitly allow training on synthetic observation records."
    )
    
    args = parser.parse_args()
    train_and_evaluate(args)
