import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import AirQuality, AirQualityPrediction
from ml.air_quality_feature_extractor import AirQualityFeatureExtractor
from ml.air_quality_splitter import TemporalAirQualitySplitter
from ml.air_quality_models import (
    NaiveAirQualityForecaster,
    HistoricalAverageAirQualityForecaster,
    calculate_air_quality_metrics
)
from ml.air_quality_train import calculate_aqi_pm25

client = TestClient(app)

@pytest.fixture
def mock_aq_dataframe():
    base_time = datetime(2026, 8, 20, 0, 0, 0, tzinfo=timezone.utc)
    records = []
    for h in range(48):
        t = base_time + timedelta(hours=h)
        for st in ["Patrapada", "IRC_Village"]:
            records.append({
                "id": len(records) + 1,
                "timestamp": t,
                "station_name": st,
                "pm25": 20.0 + h * 0.5 + (1.0 if st == "Patrapada" else 0.0),
                "pm10": 45.0 + h * 0.8,
                "co": 100.0,
                "no2": 15.0,
                "so2": 8.0,
                "o3": 25.0,
                "aqi_value": 70 + h,
                "source": "open-meteo"
            })
    return pd.DataFrame(records)

def test_feature_extractor(mock_aq_dataframe):
    mock_db = MagicMock()
    extractor = AirQualityFeatureExtractor(mock_db)
    
    df_features = extractor.extract_features(mock_aq_dataframe)
    
    assert not df_features.empty
    assert "pm25_lag_1h" in df_features.columns
    assert "pm25_lag_6h" in df_features.columns
    assert "pm25_lag_24h" in df_features.columns
    assert "pm25_rolling_mean_3h" in df_features.columns
    assert "pm25_rolling_mean_6h" in df_features.columns
    assert "pm25_rolling_mean_24h" in df_features.columns
    assert "target_pm25_6h" in df_features.columns
    assert "target_pm25_12h" in df_features.columns
    assert "target_pm25_24h" in df_features.columns
    assert "target_pm10_6h" in df_features.columns

def test_no_lookahead_leakage(mock_aq_dataframe):
    mock_db = MagicMock()
    extractor = AirQualityFeatureExtractor(mock_db)
    df_feat = extractor.extract_features(mock_aq_dataframe)
    
    patrapada = df_feat[df_feat["station_name"] == "Patrapada"].reset_index(drop=True)
    
    # At row idx 10 (t=10h), pm25_lag_1h should match pm25 at row idx 9 (t=9h)
    assert patrapada.loc[10, "pm25_lag_1h"] == patrapada.loc[9, "pm25"]
    assert patrapada.loc[10, "pm25_lag_6h"] == patrapada.loc[4, "pm25"]
    
    # Target pm25_6h at row idx 10 should match pm25 at row idx 16 (t=16h)
    assert patrapada.loc[10, "target_pm25_6h"] == patrapada.loc[16, "pm25"]

def test_temporal_splitter(mock_aq_dataframe):
    mock_db = MagicMock()
    extractor = AirQualityFeatureExtractor(mock_db)
    df_feat = extractor.extract_features(mock_aq_dataframe)
    
    df_tr, df_val, df_ts = TemporalAirQualitySplitter.split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    assert not df_tr.empty
    assert not df_val.empty
    assert not df_ts.empty
    
    assert df_tr["timestamp"].max() < df_val["timestamp"].min()
    assert df_val["timestamp"].max() < df_ts["timestamp"].min()

def test_aqi_pm25_calculator():
    assert calculate_aqi_pm25(10.0) == 42
    assert calculate_aqi_pm25(25.0) == 78
    assert calculate_aqi_pm25(50.0) == 137
    assert calculate_aqi_pm25(100.0) == 174
    assert calculate_aqi_pm25(None) is None

def test_baselines_and_metrics():
    X_train = pd.DataFrame({
        "station_name": ["Patrapada", "Patrapada", "IRC_Village", "IRC_Village"],
        "pm25_lag_1h": [25.0, 26.0, 30.0, 31.0]
    })
    y_train = np.array([26.0, 27.0, 31.0, 32.0])
    
    X_test = pd.DataFrame({
        "station_name": ["Patrapada", "IRC_Village"],
        "pm25_lag_1h": [27.0, 32.0]
    })
    y_test = np.array([28.0, 33.0])
    
    naive = NaiveAirQualityForecaster(pollutant="pm25")
    naive.fit(X_train, y_train)
    preds = naive.predict(X_test)
    assert np.array_equal(preds, np.array([27.0, 32.0]))
    
    metrics = calculate_air_quality_metrics(y_test, preds)
    assert metrics["MAE"] == 1.0
    assert metrics["RMSE"] == 1.0

def test_api_get_air_quality_forecasts():
    mock_db = MagicMock()
    
    # Create mock prediction object
    pred = MagicMock(spec=AirQualityPrediction)
    pred.id = 1
    pred.station_name = "Patrapada"
    pred.pollutant = "PM2.5"
    pred.forecast_issue_time = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    pred.target_time = datetime(2026, 8, 24, 18, 0, 0, tzinfo=timezone.utc)
    pred.horizon_hours = 6
    pred.predicted_value = 35.5
    pred.aqi_sub_index = 101
    pred.model_name = "xgboost_regressor"
    pred.model_version = "1.0.0"
    pred.is_synthetic = True
    pred.data_provenance_status = "synthetic_fallback"
    pred.created_at = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    pred.geom = from_shape(Point(85.824, 20.296), srid=4326)
    
    # Setup chain for query(AirQualityPrediction)
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [pred]
    mock_query.first.return_value = pred
    
    mock_db.query.return_value = mock_query
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/air-quality?pollutant=PM2.5&horizon_hours=6")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["properties"]["pollutant"] == "PM2.5"
        assert feat["properties"]["horizon_hours"] == 6
        assert feat["properties"]["predicted_value"] == 35.5
        assert "scientific_validation_warning" in feat["properties"]
        
        # Test get by ID
        res_id = client.get("/api/v1/air-quality/1")
        assert res_id.status_code == 200
        data_id = res_id.json()
        assert data_id["properties"]["prediction_id"] == 1
        
        # Test invalid horizon hours (422)
        res_invalid = client.get("/api/v1/air-quality?horizon_hours=5")
        assert res_invalid.status_code == 422
        
    finally:
        app.dependency_overrides.clear()
