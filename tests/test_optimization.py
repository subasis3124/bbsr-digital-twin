import pytest
from datetime import datetime, timezone
import uuid
from fastapi.testclient import TestClient

from backend.app.database import get_db
from backend.app.main import app

class MockQuery:
    def __init__(self, model=None):
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

class MockSession:
    def query(self, model):
        return MockQuery(model)

    def add(self, item):
        pass

    def commit(self):
        pass

    def refresh(self, item):
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
    app.dependency_overrides.pop(get_db, None)

from ml.optimization import (
    EmergencyDemand, EmergencyResource, DemandAssignment,
    OptimizationConstraints, OptimizationRequest, OptimizationResult,
    EmergencyOptimizationEngine
)
from ml.optimization.solver import ORToolsEmergencySolver
from ml.optimization.baseline import NearestAvailableResourceBaseline
from ml.optimization.travel_cost import TravelCostCalculator, INACCESSIBLE_COST
from ml.optimization.resources import EmergencyResourceExtractor
from ml.optimization.demand import EmergencyDemandGenerator
from ml.optimization.explanation import OptimizationExplanationBuilder


@pytest.fixture
def mock_demands():
    now_str = datetime.now(timezone.utc).isoformat()
    return [
        EmergencyDemand(
            demand_id="DEM_01",
            spatial_id="WARD_01",
            coordinates=[85.8200, 20.2700],
            timestamp=now_str,
            demand_quantity=20,
            emergency_type="medical",
            priority="CRITICAL",
            priority_weight=3.0
        ),
        EmergencyDemand(
            demand_id="DEM_02",
            spatial_id="WARD_02",
            coordinates=[85.8400, 20.2900],
            timestamp=now_str,
            demand_quantity=30,
            emergency_type="medical",
            priority="NORMAL",
            priority_weight=1.0
        )
    ]


@pytest.fixture
def mock_resources():
    now_str = datetime.now(timezone.utc).isoformat()
    return [
        EmergencyResource(
            resource_id="HOSP_01",
            resource_type="hospital",
            name="Hospital Alpha",
            coordinates=[85.8210, 20.2710],
            capacity=30,
            capacity_status="known",
            available_capacity=30,
            accessibility=1.0,
            status="AVAILABLE",
            timestamp=now_str
        ),
        EmergencyResource(
            resource_id="HOSP_02",
            resource_type="hospital",
            name="Hospital Beta",
            coordinates=[85.8410, 20.2910],
            capacity=40,
            capacity_status="known",
            available_capacity=40,
            accessibility=1.0,
            status="AVAILABLE",
            timestamp=now_str
        )
    ]


# 1. Resource Schema Validation
def test_resource_schema_validation(mock_resources):
    res = mock_resources[0]
    assert res.resource_id == "HOSP_01"
    assert res.capacity == 30
    assert res.accessibility == 1.0


# 2. Demand Schema Validation
def test_demand_schema_validation(mock_demands):
    dem = mock_demands[0]
    assert dem.demand_id == "DEM_01"
    assert dem.priority == "CRITICAL"
    assert dem.priority_weight == 3.0


# 3. Invalid Capacity Handling
def test_invalid_capacity_handling():
    res = EmergencyResource(
        resource_id="HOSP_ERR",
        resource_type="hospital",
        name="Unknown Capacity Hosp",
        coordinates=[85.82, 20.27],
        capacity=None,
        capacity_status="unknown",
        available_capacity=0,
        accessibility=1.0,
        status="AVAILABLE",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    assert res.capacity is None
    assert res.capacity_status == "unknown"


# 4. Inaccessible Resource Handling
def test_inaccessible_resource_handling(mock_demands):
    inaccessible_res = EmergencyResource(
        resource_id="HOSP_BLOCKED",
        resource_type="hospital",
        name="Flooded Hospital",
        coordinates=[85.8200, 20.2700],
        capacity=50,
        capacity_status="known",
        available_capacity=50,
        accessibility=0.0,
        status="INACCESSIBLE",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    cost, _, unit = TravelCostCalculator.compute_travel_cost(mock_demands[0], inaccessible_res)
    assert cost >= INACCESSIBLE_COST
    assert unit == "inaccessible"


# 5. Nearest Resource Baseline
def test_nearest_resource_baseline(mock_demands, mock_resources):
    allocs, summary = NearestAvailableResourceBaseline.solve(mock_demands, mock_resources)
    assert summary.total_demand == 50
    assert summary.served_demand == 50
    assert summary.unserved_demand == 0
    assert len(allocs) >= 2


# 6. Optimization Formulation (OR-Tools Solver)
def test_ortools_optimization_formulation(mock_demands, mock_resources):
    allocs, summary = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    assert summary.total_demand == 50
    assert summary.served_demand == 50
    assert summary.average_travel_cost > 0.0


# 7. Capacity Constraints Verification
def test_capacity_constraints(mock_demands):
    small_resources = [
        EmergencyResource(
            resource_id="HOSP_SMALL",
            resource_type="hospital",
            name="Small Clinic",
            coordinates=[85.8200, 20.2700],
            capacity=10,
            available_capacity=10,
            accessibility=1.0,
            status="AVAILABLE",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    ]
    allocs, summary = ORToolsEmergencySolver.solve(mock_demands, small_resources)
    # Total demand = 50, but capacity = 10 -> served = 10, unserved = 40
    assert summary.served_demand == 10
    assert summary.unserved_demand == 40
    assert "HOSP_SMALL" in summary.bottlenecks


# 8. Demand Satisfaction
def test_demand_satisfaction(mock_demands, mock_resources):
    allocs, summary = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    total_assigned_qty = sum(a.allocation_quantity for a in allocs)
    assert total_assigned_qty == 50


# 9. Travel Cost Calculation
def test_travel_cost_calculation():
    d_coord = [85.8200, 20.2700]
    r_coord = [85.8300, 20.2800]
    dist = TravelCostCalculator.haversine_distance_km(d_coord, r_coord)
    assert dist > 0.0
    assert dist < 10.0  # reasonable urban distance in Bhubaneswar


# 10. Road Closure Scenario Integration
def test_road_closure_integration(mock_demands, mock_resources):
    # Simulate road closure making HOSP_01 inaccessible
    mock_resources[0].accessibility = 0.0
    mock_resources[0].status = "INACCESSIBLE"
    
    allocs, summary = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    # All served demand must reroute to HOSP_02
    hosp1_assigned = sum(a.allocation_quantity for a in allocs if a.assigned_resource_id == "HOSP_01")
    assert hosp1_assigned == 0
    assert "HOSP_01" in summary.inaccessible_resources


# 11. Flood Scenario Integration
def test_flood_scenario_integration(mock_demands, mock_resources):
    # Flood degrades HOSP_01 accessibility to 0.2 (higher travel cost penalty)
    mock_resources[0].accessibility = 0.2
    allocs, summary = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    assert summary.served_demand > 0


# 12. Deterministic Optimization
def test_deterministic_optimization(mock_demands, mock_resources):
    allocs1, sum1 = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    allocs2, sum2 = ORToolsEmergencySolver.solve(mock_demands, mock_resources)
    assert sum1.total_travel_cost == sum2.total_travel_cost
    assert sum1.served_demand == sum2.served_demand


# 13. Baseline Comparison
def test_baseline_comparison(mock_demands, mock_resources):
    engine = EmergencyOptimizationEngine()
    result = engine.optimize(demands=mock_demands, resources=mock_resources, save=False)
    assert result.baseline_comparison is not None
    assert result.baseline_comparison.baseline_method == "NEAREST_AVAILABLE_RESOURCE"


# 14. Allocation Result Validation
def test_allocation_result_validation(mock_demands, mock_resources):
    engine = EmergencyOptimizationEngine()
    result = engine.optimize(demands=mock_demands, resources=mock_resources, save=False)
    assert len(result.allocations) > 0
    for alloc in result.allocations:
        assert alloc.assignment_status in ("ASSIGNED", "UNSERVED", "INACCESSIBLE")
        assert len(alloc.explanation) > 0


# 15. End-to-End Engine Workflow
def test_engine_workflow():
    engine = EmergencyOptimizationEngine()
    result = engine.optimize(save=False)
    assert result.run_id is not None
    assert result.engine_version == "1.0.0"
    assert result.provenance["is_synthetic"] is True


# 16. API Endpoints Tests
def test_api_list_resources():
    client = TestClient(app)
    response = client.get("/api/v1/optimization/resources")
    assert response.status_code == 200
    data = response.json()
    assert "resources" in data


def test_api_run_optimization():
    client = TestClient(app)
    payload = {
        "resource_types": ["hospital"],
        "method": "ortools_min_cost_flow",
        "save": False
    }
    response = client.post("/api/v1/optimization/emergency", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert "summary" in data
    assert "allocations" in data


def test_api_get_optimization_runs():
    client = TestClient(app)
    response = client.get("/api/v1/optimization/emergency")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
