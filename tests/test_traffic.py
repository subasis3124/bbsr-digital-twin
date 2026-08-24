import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from shapely.geometry import LineString
from geoalchemy2.shape import from_shape

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Road, TrafficPrediction
from ml.traffic_splitter import TemporalTrafficSplitter
from ml.traffic_models import NaiveForecaster, HistoricalAverageForecaster, calculate_metrics

client = TestClient(app)

def test_temporal_splitter():
    base_time = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
    data = []
    # 20 hours of data for 2 roads
    for h in range(20):
        t = base_time + timedelta(hours=h)
        for r in [1, 2]:
            data.append({
                "road_id": r,
                "timestamp": t,
                "observed_speed": 40.0 + r + h * 0.5,
                "lag_observed_speed_1h": 38.0 + r + h * 0.5,
                "lag_observed_speed_24h": 30.0 + r,
                "rolling_average_speed_3h": 35.0
            })
    df = pd.DataFrame(data)
    
    df_train, df_val, df_test = TemporalTrafficSplitter.split(df, train_ratio=0.6, val_ratio=0.2)
    
    assert not df_train.empty
    assert not df_val.empty
    assert not df_test.empty
    
    # Chronological partition checks
    assert df_train["timestamp"].max() < df_val["timestamp"].min()
    assert df_val["timestamp"].max() < df_test["timestamp"].min()

def test_baselines():
    X_train = pd.DataFrame({
        "road_id": [1, 1, 2, 2],
        "lag_observed_speed_1h": [30.0, 32.0, 45.0, 48.0],
    })
    y_train = np.array([32.0, 31.0, 48.0, 44.0])
    
    X_test = pd.DataFrame({
        "road_id": [1, 2],
        "lag_observed_speed_1h": [31.0, 44.0],
    })
    y_test = np.array([33.0, 46.0])
    
    naive = NaiveForecaster()
    naive.fit(X_train, y_train)
    preds = naive.predict(X_test)
    assert np.array_equal(preds, np.array([31.0, 44.0]))
    
    hist_avg = HistoricalAverageForecaster()
    hist_avg.fit(X_train, y_train)
    preds_hist = hist_avg.predict(X_test)
    assert preds_hist[0] == 31.5
    assert preds_hist[1] == 46.0
    
    metrics = calculate_metrics(y_test, preds)
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "R2" in metrics

def test_traffic_api_empty():
    class EmptyMockQuery:
        def __init__(self, model):
            self.model = model
            
        def join(self, *args, **kwargs):
            return self
            
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self
            
        def offset(self, *args, **kwargs):
            return self
            
        def limit(self, *args, **kwargs):
            return self
            
        def all(self):
            return []
            
        def first(self):
            return None

    class EmptyMockSession:
        def query(self, model):
            return EmptyMockQuery(model)
            
        def close(self):
            pass

    def override_db():
        yield EmptyMockSession()
        
    app.dependency_overrides[get_db] = override_db
    try:
        response = client.get("/api/v1/traffic")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 0
    finally:
        app.dependency_overrides[get_db] = get_db

def test_traffic_api_rich():
    line = LineString([(85.8, 20.2), (85.8, 20.3)])
    mock_road = Road(
        id=1,
        osm_id=123,
        name="Janpath Road",
        highway_type="primary",
        lanes=4,
        maxspeed=50,
        geom=from_shape(line, srid=4326)
    )
    
    mock_pred = TrafficPrediction(
        id=10,
        road_id=1,
        prediction_time=datetime(2026, 8, 24, 19, 0, 0, tzinfo=timezone.utc),
        forecast_horizon_minutes=60,
        predicted_speed=42.5,
        predicted_congestion_ratio=0.15,
        model_name="xgboost_regressor",
        model_version="1.0.0",
        is_synthetic=True,
        data_provenance_status="synthetic_fallback",
        road=mock_road
    )
    
    class RichMockQuery:
        def __init__(self, data, model):
            self.data = data
            self.model = model
            self._offset = 0
            self._limit = None
            
        def join(self, *args, **kwargs):
            return self
            
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self
            
        def offset(self, val):
            self._offset = val
            return self
            
        def limit(self, val):
            self._limit = val
            return self
            
        def all(self):
            res = self.data[self._offset:]
            if self._limit is not None:
                res = res[:self._limit]
            return res
            
        def first(self):
            res = self.all()
            return res[0] if res else None

    class RichMockSession:
        def query(self, model):
            return RichMockQuery([mock_pred], model)
            
        def close(self):
            pass

    def override_db_rich():
        yield RichMockSession()
        
    app.dependency_overrides[get_db] = override_db_rich
    try:
        # Bounding box test
        response = client.get("/api/v1/traffic?min_lon=85.0&min_lat=20.0&max_lon=86.0&max_lat=21.0")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["properties"]["road_id"] == 1
        assert feat["properties"]["predicted_speed"] == 42.5
        assert feat["properties"]["is_synthetic"] is True
        assert "scientific_validation_warning" in feat["properties"]
        
        # Road Detail ID test
        response = client.get("/api/v1/traffic/1")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "Feature"
        assert data["properties"]["predicted_speed"] == 42.5
    finally:
        app.dependency_overrides[get_db] = get_db
