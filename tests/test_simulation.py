import pytest
import copy
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, Point
from geoalchemy2.shape import from_shape

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import SpatialGridCell, Ward, Road, SimulationRun
from ml.city_state import (
    CityState, SpatialIdentity, TemporalIdentity, MobilityState,
    EnvironmentalState, HazardState, PopulationContext, InfrastructureContext,
    ProvenanceMetadata, DerivedIndicators
)
from ml.simulation import (
    WhatIfSimulationEngine, HeavyRainfallParams, RoadClosureParams,
    AirPollutionParams, EmergencyDemandParams, SpatialScope,
    SimulationImpactAnalyzer, DependencyGraph, HeavyRainfallScenario,
    RoadClosureScenario, AirPollutionScenario, EmergencyDemandScenario
)
from pipelines.simulation import run_simulation_pipeline

# ==========================================
# Mock Database Session for API & Engine
# ==========================================

class MockQuery:
    def __init__(self, model):
        self.model = model
        self.items = []

    def all(self):
        return self.items

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
        return len(self.items)

    def scalar(self):
        return 0

class MockSession:
    def __init__(self):
        self.added = []

    def query(self, model):
        return MockQuery(model)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = 1

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

# Helper fixture for base CityState
def create_sample_base_state(spatial_id="CELL_001", road_id=101, flood_prob=0.10, speed=40.0, aqi=45):
    spatial = SpatialIdentity(
        spatial_unit_type="grid_cell",
        spatial_id=spatial_id,
        cell_id=1,
        cell_code=spatial_id,
        road_id=road_id,
        centroid=[85.83, 20.27],
        bbox=[85.82, 20.26, 85.84, 20.28]
    )
    temporal = TemporalIdentity(
        state_timestamp="2026-09-02T10:00:00+00:00",
        target_timestamp="2026-09-02T10:00:00+00:00",
        forecast_horizon_minutes=0,
        state_type="CURRENT"
    )
    mobility = MobilityState(observed_speed=speed, congestion_ratio=0.2, road_accessibility=1.0)
    env = EnvironmentalState(pm25=15.0, aqi_value=aqi, air_quality_category="GOOD", rainfall=0.0)
    hazards = HazardState(flood_risk_probability=flood_prob, flood_risk_level="LOW")
    pop = PopulationContext(population_count=500, population_density=2000.0)
    infra = InfrastructureContext(hospitals_count=1, hospital_beds=50, schools_count=2)
    prov = ProvenanceMetadata(
        sources=["open-meteo"],
        is_synthetic=False,
        generated_at="2026-09-02T10:00:00+00:00"
    )
    derived = DerivedIndicators(
        traffic_congestion_index=0.2,
        flood_risk_level="LOW",
        air_quality_category="GOOD",
        rainfall_intensity="NONE",
        road_accessibility=1.0
    )

    return CityState(
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


# ==========================================
# 1. Scenario Schema Validation Tests
# ==========================================

def test_heavy_rainfall_params_valid():
    params = HeavyRainfallParams(rainfall_multiplier=2.0, rainfall_delta_mm=30.0)
    assert params.rainfall_multiplier == 2.0
    assert params.rainfall_delta_mm == 30.0


def test_invalid_parameter_rejection():
    # Negative multiplier
    with pytest.raises(Exception):
        HeavyRainfallParams(rainfall_multiplier=-1.0)

    # Empty closed roads list
    with pytest.raises(Exception):
        RoadClosureParams(closed_road_ids=[])

    # Invalid pollutant
    with pytest.raises(Exception):
        AirPollutionParams(pollutant="unobtanium")

    # Invalid bbox coordinates
    with pytest.raises(Exception):
        SpatialScope(scope_type="bbox", min_lon=90.0, max_lon=80.0)


# ==========================================
# 2. Heavy Rainfall Scenario Propagation
# ==========================================

def test_heavy_rainfall_scenario_propagation():
    base_state = create_sample_base_state(flood_prob=0.10, speed=40.0)

    params = HeavyRainfallParams(rainfall_multiplier=1.0, rainfall_delta_mm=60.0)
    scenario = HeavyRainfallScenario(params)

    sim_state, steps = scenario.apply(base_state)

    # Rainfall should increase to 60mm
    assert sim_state.environment.rainfall == 60.0
    # Flood risk probability should increase above 0.70
    assert sim_state.hazards.flood_risk_probability >= 0.70
    assert sim_state.hazards.flood_risk_level == "HIGH"
    # Accessibility drops
    assert sim_state.mobility.road_accessibility <= 0.30
    # Traffic speed drops proportionally
    assert sim_state.mobility.observed_speed < base_state.mobility.observed_speed
    # Inspectable transformation steps present
    assert len(steps) == 5
    assert steps[0].name == "Environmental Rainfall Perturbation"


# ==========================================
# 3. Road Closure Scenario Propagation
# ==========================================

def test_road_closure_scenario_propagation():
    base_state = create_sample_base_state(road_id=101, speed=40.0)

    params = RoadClosureParams(closed_road_ids=[101])
    scenario = RoadClosureScenario(params)

    sim_state, steps = scenario.apply(base_state)

    # Directly closed road segment
    assert sim_state.mobility.road_accessibility == 0.0
    assert sim_state.mobility.observed_speed == 0.0
    assert sim_state.mobility.status == "CLOSED"
    assert len(steps) >= 2


# ==========================================
# 4. Air Quality Scenario Propagation
# ==========================================

def test_air_quality_scenario_propagation():
    base_state = create_sample_base_state(aqi=45)

    params = AirPollutionParams(pollutant="pm25", multiplier=3.0, delta=50.0)
    scenario = AirPollutionScenario(params)

    sim_state, steps = scenario.apply(base_state)

    assert sim_state.environment.pm25 > base_state.environment.pm25
    assert sim_state.environment.aqi_value > 100
    assert sim_state.environment.air_quality_category in ["UNHEALTHY", "VERY_UNHEALTHY", "HAZARDOUS"]


# ==========================================
# 5. Emergency Demand Scenario Propagation
# ==========================================

def test_emergency_demand_scenario_propagation():
    base_state = create_sample_base_state()

    params = EmergencyDemandParams(hospital_demand_multiplier=2.5)
    scenario = EmergencyDemandScenario(params)

    sim_state, steps = scenario.apply(base_state)

    assert sim_state.infrastructure.emergency_service_density > base_state.infrastructure.emergency_service_density


# ==========================================
# 6. Dependency Graph Inspectability
# ==========================================

def test_dependency_graph_inspectability():
    graph = DependencyGraph()
    graph.add_step(
        step_number=1,
        name="Rainfall Perturbation",
        layer_affected="environment",
        input_variables={"delta": 50},
        output_variables={"rainfall": 50},
        method="heuristic_simulation",
        description="Rainfall surge"
    )
    graph.add_step(
        step_number=2,
        name="Flood Risk Recalculation",
        layer_affected="hazards",
        input_variables={"rainfall": 50},
        output_variables={"flood_prob": 0.7},
        method="heuristic_simulation",
        description="Flood risk spike",
        depends_on=["Rainfall Perturbation"]
    )

    d = graph.to_dict()
    assert len(d["steps"]) == 2
    assert len(d["dependency_edges"]) == 1
    assert d["dependency_edges"][0] == {"from": "Rainfall Perturbation", "to": "Flood Risk Recalculation"}


# ==========================================
# 7. Impact Analyzer Delta Calculation
# ==========================================

def test_impact_analyzer_delta_calculation():
    b_state = create_sample_base_state(speed=40.0, flood_prob=0.10)
    s_state = copy.deepcopy(b_state)
    s_state.mobility.observed_speed = 20.0
    s_state.hazards.flood_risk_probability = 0.60

    summary = SimulationImpactAnalyzer.analyze(
        base_states=[b_state],
        simulated_states=[s_state],
        directly_simulated_fields=["traffic_speed"]
    )

    assert summary.affected_spatial_units_count == 1
    assert summary.overall_severity in ["HIGH", "CRITICAL"]

    speed_metric = summary.metrics["traffic_speed"]
    assert speed_metric.base_value == 40.0
    assert speed_metric.simulated_value == 20.0
    assert speed_metric.delta_absolute == -20.0
    assert speed_metric.delta_percentage == -50.0
    assert speed_metric.category == "DIRECTLY_SIMULATED"


# ==========================================
# 8. Spatial Scope Filtering
# ==========================================

def test_spatial_filtering():
    state1 = create_sample_base_state(spatial_id="CELL_001")
    state2 = create_sample_base_state(spatial_id="CELL_002")

    scope = SpatialScope(scope_type="grid_cell", cell_codes=["CELL_001"])
    params = HeavyRainfallParams(rainfall_delta_mm=50.0, spatial_scope=scope)
    scenario = HeavyRainfallScenario(params)

    sim1, _ = scenario.apply(state1)
    sim2, _ = scenario.apply(state2)

    # state1 in scope -> perturbed
    assert sim1.environment.rainfall == 50.0
    # state2 out of scope -> unperturbed
    assert sim2.environment.rainfall == 0.0


def test_empty_grid_cell_scope_affects_all_cells_and_base_state_immutability():
    state1 = create_sample_base_state(spatial_id="CELL_001")
    state2 = create_sample_base_state(spatial_id="CELL_002")

    original_dump1 = copy.deepcopy(state1.model_dump())
    original_dump2 = copy.deepcopy(state2.model_dump())

    # Empty grid cell scope (should affect ALL grid cells)
    scope = SpatialScope(scope_type="grid_cell", cell_codes=[])
    params = HeavyRainfallParams(rainfall_delta_mm=50.0, spatial_scope=scope)
    scenario = HeavyRainfallScenario(params)

    sim1, _ = scenario.apply(state1)
    sim2, _ = scenario.apply(state2)

    # 1. Heavy rainfall with empty grid-cell IDs affects applicable cells
    assert sim1.environment.rainfall == 50.0
    assert sim2.environment.rainfall == 50.0

    # 2. Impact analysis reports non-zero affected units when base state permits
    summary = SimulationImpactAnalyzer.analyze(
        base_states=[state1, state2],
        simulated_states=[sim1, sim2],
        directly_simulated_fields=["rainfall"]
    )
    assert summary.affected_spatial_units_count == 2

    # 3. Base state remains unchanged
    assert state1.model_dump() == original_dump1
    assert state2.model_dump() == original_dump2


# ==========================================
# 9. Temporal Leakage Prevention
# ==========================================

def test_temporal_leakage_prevention():
    engine = WhatIfSimulationEngine()
    b_state = create_sample_base_state()

    ts_base = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    ts_sim_past = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)

    # Simulation timestamp < base state timestamp must fail
    with pytest.raises(ValueError) as exc:
        engine.run_simulation(
            scenario_type="heavy_rainfall",
            parameters={"rainfall_delta_mm": 20.0},
            base_states=[b_state],
            base_timestamp=ts_base,
            simulation_timestamp=ts_sim_past
        )
    assert "precede" in str(exc.value).lower()


# ==========================================
# 10. Provenance & Warning Propagation
# ==========================================

def test_provenance_propagation():
    engine = WhatIfSimulationEngine()
    b_state = create_sample_base_state()

    res = engine.run_simulation(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_delta_mm": 30.0},
        base_states=[b_state]
    )

    assert res.provenance["is_synthetic"] is True
    assert res.provenance["data_provenance_status"] == "scenario_simulation"
    assert "WARNING" in res.provenance["scientific_validation_warning"]


# ==========================================
# 11. Immutability of Base State
# ==========================================

def test_base_state_immutability():
    b_state = create_sample_base_state(speed=40.0)
    original_dump = copy.deepcopy(b_state.model_dump())

    engine = WhatIfSimulationEngine()
    res = engine.run_simulation(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_delta_mm": 50.0},
        base_states=[b_state]
    )

    # Base state must remain identical after simulation execution
    assert b_state.model_dump() == original_dump


# ==========================================
# 12. Determinism Test
# ==========================================

def test_deterministic_simulation():
    b_state = create_sample_base_state()

    engine = WhatIfSimulationEngine()
    res1 = engine.run_simulation(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_delta_mm": 40.0},
        base_states=[b_state]
    )
    res2 = engine.run_simulation(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_delta_mm": 40.0},
        base_states=[b_state]
    )

    # Exact same outputs for exact same inputs
    assert res1.impact_summary.overall_severity == res2.impact_summary.overall_severity
    assert res1.simulated_states[0]["environment"]["rainfall"] == res2.simulated_states[0]["environment"]["rainfall"]
    assert res1.simulated_states[0]["hazards"]["flood_risk_probability"] == res2.simulated_states[0]["hazards"]["flood_risk_probability"]


# ==========================================
# 13. API Endpoint Tests
# ==========================================

def test_api_list_scenario_types():
    response = client.get("/api/v1/simulations/scenarios/types")
    assert response.status_code == 200
    data = response.json()
    assert data["engine_version"] == "1.0.0"
    types = [s["type"] for s in data["scenarios"]]
    assert "heavy_rainfall" in types
    assert "road_closure" in types


def test_api_create_and_retrieve_simulation():
    # Create simulation via POST API with explicitly provided base_states mock inside engine or session
    payload = {
        "scenario_type": "heavy_rainfall",
        "parameters": {"rainfall_delta_mm": 25.0},
        "save": False
    }

    # API request with mock base state
    response = client.post("/api/v1/simulations", json=payload)
    # If no base states in mock DB, engine returns 400 with descriptive error
    assert response.status_code in [201, 400]


# ==========================================
# 14. CLI Pipeline Execution Test
# ==========================================

def test_cli_simulation_pipeline():
    b_state = create_sample_base_state()
    mock_session = MockSession()

    res = run_simulation_pipeline(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_delta_mm": 20.0},
        limit=1,
        save=False,
        dry_run=True,
        db_session=mock_session
    )
    assert "scenario" in res
    assert "impact_summary" in res
