import pytest
from datetime import datetime, timezone
from shapely.geometry import Polygon, Point
from geoalchemy2.shape import from_shape

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import SpatialGridCell, Ward, CityStateSnapshot, SatelliteFeature, Prediction
from ml.city_state import (
    CityState, SpatialIdentity, TemporalIdentity, MobilityState,
    EnvironmentalState, HazardState, PopulationContext, InfrastructureContext,
    ProvenanceMetadata, DerivedIndicators, CityStateAggregator,
    CityStateValidator, DataSourceRegistry
)
from pipelines.city_state import run_city_state_pipeline
from fastapi.testclient import TestClient

# ==========================================
# Mock Database Session for API & Pipeline Tests
# ==========================================

class MockQuery:
    def __init__(self, model):
        self.model = model

    def all(self):
        return []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def count(self):
        return 0

    def scalar(self):
        return 0

class MockSession:
    def query(self, model):
        return MockQuery(model)

    def add(self, obj):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def close(self):
        pass

def override_get_db():
    db = MockSession()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_mock_db_override():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ==========================================
# 1. Pydantic Schema & Serialization Tests
# ==========================================

def test_city_state_schema_instantiation():
    spatial = SpatialIdentity(
        spatial_unit_type="grid_cell",
        spatial_id="CELL_001",
        cell_id=1,
        cell_code="CELL_001",
        centroid=[85.83, 20.27],
        bbox=[85.82, 20.26, 85.84, 20.28]
    )
    temporal = TemporalIdentity(
        state_timestamp="2026-09-02T10:00:00+00:00",
        target_timestamp="2026-09-02T11:00:00+00:00",
        forecast_horizon_minutes=60,
        state_type="FORECAST"
    )
    mobility = MobilityState(observed_speed=40.0, congestion_ratio=0.2)
    env = EnvironmentalState(pm25=25.0, aqi_value=75, air_quality_category="MODERATE")
    hazards = HazardState(flood_risk_probability=0.1, flood_risk_level="LOW")
    pop = PopulationContext(population_count=500, population_density=2000.0)
    infra = InfrastructureContext(hospitals_count=1, hospital_beds=50)
    prov = ProvenanceMetadata(
        sources=["open-meteo"],
        is_synthetic=True,
        scientific_validation_warning="Synthetic validation warning",
        generated_at="2026-09-02T10:00:00+00:00"
    )
    derived = DerivedIndicators(
        traffic_congestion_index=0.2,
        flood_risk_level="LOW",
        air_quality_category="MODERATE",
        rainfall_intensity="NONE"
    )

    c_state = CityState(
        location=spatial,
        time=temporal,
        mobility=mobility,
        environment=env,
        hazards=hazards,
        population=pop,
        infrastructure=infra,
        provenance=prov,
        derived=derived
    )

    assert c_state.location.spatial_id == "CELL_001"
    assert c_state.time.state_type == "FORECAST"
    assert c_state.time.forecast_horizon_minutes == 60
    assert c_state.provenance.is_synthetic is True

    dumped = c_state.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["location"]["spatial_id"] == "CELL_001"


# ==========================================
# 2. Validation Engine Tests
# ==========================================

def test_city_state_validator_valid():
    spatial = SpatialIdentity(spatial_id="CELL_100", centroid=[85.8, 20.2])
    temporal = TemporalIdentity(
        state_timestamp="2026-09-02T10:00:00+00:00",
        target_timestamp="2026-09-02T10:00:00+00:00",
        forecast_horizon_minutes=0,
        state_type="CURRENT"
    )
    c_state = CityState(
        location=spatial,
        time=temporal,
        mobility=MobilityState(observed_speed=30.0, congestion_ratio=0.4),
        environment=EnvironmentalState(humidity=65.0, ndvi=0.4),
        hazards=HazardState(flood_risk_probability=0.2),
        population=PopulationContext(),
        infrastructure=InfrastructureContext(),
        provenance=ProvenanceMetadata(
            is_synthetic=True,
            scientific_validation_warning="Synthetic warning",
            generated_at="2026-09-02T10:00:00+00:00"
        ),
        derived=DerivedIndicators()
    )

    val_res = CityStateValidator.validate(c_state)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0


def test_city_state_validator_invalid_temporal_leakage():
    spatial = SpatialIdentity(spatial_id="CELL_101")
    # Target timestamp PRECEDES state timestamp -> invalid temporal leakage
    temporal = TemporalIdentity(
        state_timestamp="2026-09-02T12:00:00+00:00",
        target_timestamp="2026-09-02T10:00:00+00:00",
        forecast_horizon_minutes=60,
        state_type="FORECAST"
    )
    c_state = CityState(
        location=spatial,
        time=temporal,
        mobility=MobilityState(),
        environment=EnvironmentalState(),
        hazards=HazardState(),
        population=PopulationContext(),
        infrastructure=InfrastructureContext(),
        provenance=ProvenanceMetadata(generated_at="2026-09-02T10:00:00+00:00"),
        derived=DerivedIndicators()
    )

    val_res = CityStateValidator.validate(c_state)
    assert val_res.is_valid is False
    assert any("precede" in err.lower() for err in val_res.errors)


def test_city_state_validator_nan_inf_check():
    spatial = SpatialIdentity(spatial_id="CELL_102")
    temporal = TemporalIdentity(
        state_timestamp="2026-09-02T10:00:00+00:00",
        target_timestamp="2026-09-02T10:00:00+00:00",
        forecast_horizon_minutes=0,
        state_type="CURRENT"
    )
    # NaN in flood probability
    c_state = CityState(
        location=spatial,
        time=temporal,
        mobility=MobilityState(),
        environment=EnvironmentalState(),
        hazards=HazardState(flood_risk_probability=float('nan')),
        population=PopulationContext(),
        infrastructure=InfrastructureContext(),
        provenance=ProvenanceMetadata(generated_at="2026-09-02T10:00:00+00:00"),
        derived=DerivedIndicators()
    )

    val_res = CityStateValidator.validate(c_state)
    assert val_res.is_valid is False
    assert any("nan or inf" in err.lower() for err in val_res.errors)


# ==========================================
# 3. Data Source Registry Tests
# ==========================================

def test_data_source_registry_lookup():
    weather_info = DataSourceRegistry.get_source_info("weather")
    assert weather_info["source_type"] == "sensor_api"
    assert weather_info["default_source"] == "open-meteo"

    gnn_info = DataSourceRegistry.get_source_info("gnn_traffic_forecast")
    assert gnn_info["is_synthetic"] is True
    assert "WARNING" in gnn_info["warning"]


# ==========================================
# 4. Aggregator & Database Session Tests
# ==========================================

def test_aggregator_grid_cell_execution():
    poly = Polygon([(85.82, 20.26), (85.84, 20.26), (85.84, 20.28), (85.82, 20.28), (85.82, 20.26)])
    pt = Point(85.83, 20.27)

    grid_cell = SpatialGridCell(
        id=1,
        cell_code="GRID_TEST_001",
        geom=from_shape(poly, srid=4326),
        centroid=from_shape(pt, srid=4326)
    )

    session = MockSession()
    aggregator = CityStateAggregator(session)

    c_state = aggregator.aggregate_grid_cell(grid_cell, forecast_horizon_minutes=30)
    assert c_state.location.spatial_id == "GRID_TEST_001"
    assert c_state.time.forecast_horizon_minutes == 30
    assert c_state.time.state_type == "FORECAST"
    assert c_state.location.centroid == [85.83, 20.27]


def test_aggregator_ward_execution():
    poly = Polygon([(85.80, 20.20), (85.85, 20.20), (85.85, 20.25), (85.80, 20.25), (85.80, 20.20)])
    ward = Ward(
        id=10,
        ward_number=10,
        name="Saheed Nagar",
        population_est=25000,
        geom=from_shape(poly, srid=4326)
    )

    session = MockSession()
    aggregator = CityStateAggregator(session)

    c_state = aggregator.aggregate_ward(ward, forecast_horizon_minutes=0)
    assert c_state.location.spatial_id == "10"
    assert c_state.location.ward_number == 10
    assert c_state.population.population_count == 25000
    assert c_state.derived.flood_risk_level == "LOW"


# ==========================================
# 5. API Endpoint Integration Tests
# ==========================================

def test_api_city_state_metadata():
    response = client.get("/api/v1/city-state/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["engine_name"] == "Unified City State Engine"
    assert data["state_schema_version"] == "1.0.0"
    assert "grid_cell" in data["canonical_spatial_units"]
    assert "WARNING" in data["scientific_validation_warning"]


def test_api_city_states_collection_empty_fallback():
    response = client.get("/api/v1/city-state")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data


def test_api_city_state_by_id_not_found():
    response = client.get("/api/v1/city-state/NON_EXISTENT_CELL_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_city_state_generate():
    response = client.post("/api/v1/city-state/generate?limit=5&save=false")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "generated_count" in data


# ==========================================
# 6. CLI Pipeline Execution Test
# ==========================================

def test_cli_pipeline_run():
    res = run_city_state_pipeline(
        timestamp_str=None,
        forecast_horizon_minutes=15,
        spatial_unit="grid_cell",
        limit=2,
        save=False,
        dry_run=True,
        strict_validate=True,
        db_session=MockSession()
    )
    assert "processed_count" in res
    assert "validation_failures" in res
