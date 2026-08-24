import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from shapely.geometry import Polygon, Point
from geoalchemy2.shape import from_shape, to_shape
import datetime

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Prediction, SpatialGridCell, FloodEvent, SatelliteFeature, PopulationGrid

client = TestClient(app)

# Helper function to generate mock geometry
def make_mock_polygon():
    polygon = Polygon([(85.80, 20.20), (85.80, 20.21), (85.81, 20.21), (85.81, 20.20), (85.80, 20.20)])
    return from_shape(polygon, srid=4326)

def make_mock_centroid():
    point = Point(85.805, 20.205)
    return from_shape(point, srid=4326)

# Test 1: Empty results GeoJSON response
def test_get_flood_risk_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.join.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.count.return_value = 0 # No historical flood events -> is_synthetic=True
    
    # Temporarily override dependency injection
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/flood-risk")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 0
    finally:
        # Reset override
        app.dependency_overrides.pop(get_db, None)

# Test 2: Results with mock predictions
def test_get_flood_risk_with_data():
    mock_db = MagicMock()
    
    # Create a mock pair of Prediction and SpatialGridCell
    mock_pred = Prediction(
        id=101,
        cell_id=5,
        model_name="xgboost",
        model_version="1.0.0",
        prediction_time=datetime.datetime(2026, 8, 24, 18, 0, 0, tzinfo=datetime.timezone.utc),
        predicted_probability=0.87,
        predicted_class="HIGH",
        feature_importance_shap={"elevation": -0.4, "dist_to_water": -0.8}
    )
    
    mock_cell = SpatialGridCell(
        id=5,
        cell_code="BBSR-GRID-5",
        geom=make_mock_polygon(),
        centroid=make_mock_centroid()
    )
    
    # Mocking standard query results
    mock_db.query.return_value.join.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
        (mock_pred, mock_cell)
    ]
    mock_db.query.return_value.count.return_value = 0 # 0 historical events -> is_synthetic = True
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/flood-risk?risk_level=HIGH")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        
        feat = data["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Polygon"
        
        props = feat["properties"]
        assert props["prediction_id"] == 101
        assert props["cell_code"] == "BBSR-GRID-5"
        assert props["predicted_class"] == "HIGH"
        assert props["predicted_probability"] == 0.87
        assert props["is_synthetic"] is True
        assert props["data_provenance_status"] == "synthetic_fallback"
        assert "scientific_validation_warning" in props
        assert "synthetic validation labels" in props["scientific_validation_warning"]
    finally:
        app.dependency_overrides.pop(get_db, None)

# Test 3: Invalid Bounding Box Queries
def test_get_flood_risk_invalid_bbox():
    response = client.get("/api/v1/flood-risk?min_lon=85.80&min_lat=20.20") # incomplete parameters
    assert response.status_code == 400
    assert "all 4 coordinates" in response.json()["detail"]

    response = client.get("/api/v1/flood-risk?min_lon=85.85&min_lat=20.20&max_lon=85.80&max_lat=20.30") # min_lon > max_lon
    assert response.status_code == 400
    assert "Invalid bounding box" in response.json()["detail"]

# Test 4: Single prediction lookup
def test_get_prediction_by_id():
    mock_db = MagicMock()
    
    mock_pred = Prediction(
        id=77,
        cell_id=9,
        model_name="random_forest",
        model_version="1.0.0",
        prediction_time=datetime.datetime(2026, 8, 24, 18, 0, 0, tzinfo=datetime.timezone.utc),
        predicted_probability=0.22,
        predicted_class="LOW",
        feature_importance_shap={"elevation": 0.5, "slope": 0.1}
    )
    
    mock_cell = SpatialGridCell(
        id=9,
        cell_code="BBSR-GRID-9",
        geom=make_mock_polygon(),
        centroid=make_mock_centroid()
    )
    
    mock_sat = SatelliteFeature(
        cell_id=9,
        timestamp=datetime.datetime(2026, 8, 24, 18, 0, 0, tzinfo=datetime.timezone.utc),
        elevation=22.5,
        slope=1.8,
        ndvi=0.35,
        ndwi=0.1,
        ndbi=-0.2
    )
    
    mock_pop = PopulationGrid(
        population_count=120,
        geom=make_mock_polygon()
    )
    
    # Setup mock returns
    mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = (mock_pred, mock_cell)
    # mock_db.query(SatelliteFeature)...
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_sat
    # mock_db.query(PopulationGrid)...
    mock_db.query.return_value.filter.return_value.first.return_value = mock_pop
    mock_db.query.return_value.count.return_value = 0 # Synthetic
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/flood-risk/77")
        assert response.status_code == 200
        feat = response.json()
        assert feat["type"] == "Feature"
        
        props = feat["properties"]
        assert props["prediction_id"] == 77
        assert props["predicted_class"] == "LOW"
        assert props["predicted_probability"] == 0.22
        assert props["feature_importance_shap"]["elevation"] == 0.5
        assert props["environmental_features"]["elevation_m"] == 22.5
        assert props["environmental_features"]["slope_deg"] == 1.8
        assert props["environmental_features"]["ndvi"] == 0.35
        assert props["environmental_features"]["population_count"] == 120
    finally:
        app.dependency_overrides.pop(get_db, None)

# Test 5: Single prediction lookup 404 behavior
def test_get_prediction_by_id_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        response = client.get("/api/v1/flood-risk/999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)
