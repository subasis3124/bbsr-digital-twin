import os
import sys
sys.path.insert(0, ".")
import argparse
import datetime
import numpy as np
import pandas as pd
import mlflow
import mlflow.xgboost
import xgboost as xgb
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from backend.app.database import SessionLocal
from backend.app.models import AirQuality, AirQualityPrediction
from pipelines.sources.air_quality import AirQualityPipeline
from ml.air_quality_feature_extractor import AirQualityFeatureExtractor
from ml.air_quality_splitter import TemporalAirQualitySplitter
from ml.air_quality_models import (
    NaiveAirQualityForecaster,
    HistoricalAverageAirQualityForecaster,
    calculate_air_quality_metrics
)

def setup_mlflow():
    default_db = os.path.join(os.getcwd(), "mlflow_bbsr.db").replace("\\", "/")
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{default_db}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("Bhubaneswar_Air_Quality_Forecasting")
    print(f"MLflow configured with tracking database: {tracking_uri}")

def calculate_aqi_pm25(pm25_val: float) -> Optional[int]:
    """
    Calculates EPA standard AQI sub-index for PM2.5.
    """
    if pm25_val is None or np.isnan(pm25_val) or pm25_val < 0:
        return None

    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500)
    ]
    for clo, chi, ilo, ihi in breakpoints:
        if clo <= pm25_val <= chi:
            aqi = ((ihi - ilo) / (chi - clo)) * (pm25_val - clo) + ilo
            return int(round(aqi))

    if pm25_val > 500.4:
        return 500
    return 0

def train_and_evaluate(args):
    db: Session = SessionLocal()

    try:
        # 1. Verify or trigger ETL data load
        obs_count = db.query(AirQuality).count()
        if obs_count == 0:
            print("No air quality records found in database. Running Phase 5 AirQualityPipeline ETL...")
            pipeline = AirQualityPipeline()
            pipeline.run()
            obs_count = db.query(AirQuality).count()
            print(f"Ingested {obs_count} air quality observations into database.")

        if obs_count == 0:
            raise ValueError("Failed to obtain air quality records.")

        print(f"Loaded {obs_count} air quality observations from database.")

        # 2. Extract Features
        extractor = AirQualityFeatureExtractor(db)
        df_aq, df_weather = extractor.load_raw_data()
        df_features = extractor.extract_features(df_aq, df_weather)

        if df_features.empty:
            print("Feature matrix is empty. Ensure sufficient chronological observation spans.")
            return

        # Check provenance
        open_meteo_count = db.query(AirQuality).filter(AirQuality.source.like("%open-meteo%")).count()
        synthetic_count = db.query(AirQuality).filter(AirQuality.source.like("%synthetic%")).count()
        is_synthetic = (open_meteo_count > 0 or synthetic_count > 0 or obs_count < 48)
        data_provenance = "synthetic_fallback" if is_synthetic else "validated_model"

        if is_synthetic and not args.allow_synthetic:
            print("BLOCKER: Synthetically/Forecast-derived observations detected, but --allow-synthetic was not set.")
            print("To train models, re-run with: python ml/air_quality_train.py --allow-synthetic")
            return

        # 3. Chronological Split
        df_train, df_val, df_test = TemporalAirQualitySplitter.split(df_features)
        print(f"Dataset Chronologically Partitioned: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)}")

        # Define candidate pollutants and forecast horizons
        pollutants = ["pm25", "pm10"]
        horizons = [6, 12, 24]

        # Base feature columns (excluding metadata and targets)
        exclude_cols = {
            "id", "timestamp", "station_name", "source", "aqi_value"
        }
        for p in pollutants:
            exclude_cols.add(p)
            for h in horizons:
                exclude_cols.add(f"target_{p}_{h}h")

        feature_cols = [c for c in df_features.columns if c not in exclude_cols]

        results_summary = {}
        trained_models = {}

        setup_mlflow()

        with mlflow.start_run(run_name=f"air_quality_model_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            mlflow.log_params({
                "is_synthetic": is_synthetic,
                "data_provenance": data_provenance,
                "total_observations": obs_count,
                "train_records": len(df_train),
                "test_records": len(df_test),
                "horizons": horizons,
                "pollutants": pollutants
            })

            for pollutant in pollutants:
                # Check target availability
                if pollutant not in df_features.columns or df_features[pollutant].dropna().empty:
                    print(f"Pollutant '{pollutant}' has no valid data. Marking as unavailable.")
                    continue

                for h in horizons:
                    target_col = f"target_{pollutant}_{h}h"
                    if target_col not in df_features.columns:
                        continue

                    # Filter rows with valid targets
                    tr_subset = df_train.dropna(subset=[target_col] + feature_cols).copy()
                    val_subset = df_val.dropna(subset=[target_col] + feature_cols).copy()
                    ts_subset = df_test.dropna(subset=[target_col] + feature_cols).copy()

                    if tr_subset.empty or ts_subset.empty:
                        # Fallback to train without dropna on test if small dataset
                        tr_subset = df_train.fillna(0.0).copy()
                        ts_subset = df_test.fillna(0.0).copy()

                    X_tr, y_tr = tr_subset[feature_cols], tr_subset[target_col].values
                    X_ts, y_ts = ts_subset[feature_cols], ts_subset[target_col].values

                    # -- Baseline 1: Naive
                    naive = NaiveAirQualityForecaster(pollutant=pollutant)
                    naive.fit(X_tr, y_tr)
                    preds_naive = naive.predict(X_ts)
                    metrics_naive = calculate_air_quality_metrics(y_ts, preds_naive)

                    # -- Baseline 2: Historical Average
                    hist_avg = HistoricalAverageAirQualityForecaster(pollutant=pollutant)
                    hist_avg.fit(tr_subset, y_tr)
                    preds_hist = hist_avg.predict(ts_subset)
                    metrics_hist = calculate_air_quality_metrics(y_ts, preds_hist)

                    # -- XGBoost Regressor
                    xgb_reg = xgb.XGBRegressor(
                        n_estimators=50,
                        max_depth=5,
                        learning_rate=0.08,
                        random_state=42
                    )
                    xgb_reg.fit(X_tr, y_tr)
                    preds_xgb = xgb_reg.predict(X_ts)
                    metrics_xgb = calculate_air_quality_metrics(y_ts, preds_xgb)

                    key = f"{pollutant.upper()}_{h}h"
                    results_summary[key] = {
                        "Naive": metrics_naive,
                        "HistAvg": metrics_hist,
                        "XGBoost": metrics_xgb
                    }
                    trained_models[(pollutant, h)] = (xgb_reg, feature_cols)

                    print(f"\n--- Metrics [{key}] ---")
                    print(f"  Naive:    {metrics_naive}")
                    print(f"  HistAvg:  {metrics_hist}")
                    print(f"  XGBoost:  {metrics_xgb}")

                    # MLflow Logging
                    for metric_name, val in metrics_xgb.items():
                        mlflow.log_metric(f"{key}_{metric_name.lower()}", val)

            print("\nSuccessfully logged experiment metrics to MLflow.")

        # 4. Prediction Generation & DB Storage
        last_timestamp = df_features["timestamp"].max()
        issue_timestamp = last_timestamp

        # Clear existing predictions before saving new ones to maintain idempotency
        db.query(AirQualityPrediction).delete()
        db.commit()

        forecasts = []
        station_names = df_features["station_name"].unique()

        # Fixed point coordinates for Bhubaneswar Central station
        station_geom = from_shape(Point(85.824, 20.296), srid=4326)

        for st in station_names:
            st_data = df_features[df_features["station_name"] == st].sort_values("timestamp")
            if st_data.empty:
                continue

            latest_row = st_data.iloc[-1:].copy()

            for (pollutant, h), (model, feat_cols) in trained_models.items():
                X_future = latest_row[feat_cols]
                pred_val = float(model.predict(X_future)[0])
                pred_val = max(0.0, float(round(pred_val, 2)))

                target_time = issue_timestamp + pd.Timedelta(hours=h)
                aqi_sub = calculate_aqi_pm25(pred_val) if pollutant == "pm25" else None

                forecast = AirQualityPrediction(
                    station_name=st,
                    pollutant=pollutant.upper(),
                    forecast_issue_time=issue_timestamp.to_pydatetime(),
                    target_time=target_time.to_pydatetime(),
                    horizon_hours=h,
                    predicted_value=pred_val,
                    aqi_sub_index=aqi_sub,
                    model_name="xgboost_regressor",
                    model_version="1.0.0",
                    geom=station_geom,
                    is_synthetic=is_synthetic,
                    data_provenance_status=data_provenance
                )
                forecasts.append(forecast)

        db.bulk_save_objects(forecasts)
        db.commit()
        print(f"Stored {len(forecasts)} air quality forecast records in database 'air_quality_predictions' table.")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - Air Quality Forecasting Pipeline")
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Explicitly allow training on synthetic/forecast-derived observation records."
    )

    args = parser.parse_args()
    train_and_evaluate(args)
