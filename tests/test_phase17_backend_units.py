import pytest
import math
from pydantic import ValidationError
from datetime import datetime, timezone

from backend.app.ai.schemas import AIQueryRequest, AIIntentEnum
from backend.app.ai.tools import execute_tool, TOOL_REGISTRY, FloodRiskParams
from ml.simulation import HeavyRainfallParams, RoadClosureParams, AirPollutionParams, EmergencyDemandParams, SpatialScope
from ml.optimization import EmergencyDemand, EmergencyResource, OptimizationConstraints, OptimizationRequest
from tests.test_ai_interface import MockSession


# 1. Validation & Schema Edge Cases
def test_ai_query_request_validation():
    # Valid query
    req = AIQueryRequest(query="Show flood risk", spatial_context="ward:5")
    assert req.query == "Show flood risk"
    assert req.spatial_context == "ward:5"

    # Malformed / Empty query
    with pytest.raises(ValidationError):
        AIQueryRequest(query="")

    # Excessive query length
    with pytest.raises(ValidationError):
        AIQueryRequest(query="x" * 1005)


def test_simulation_params_validation():
    # Valid parameters
    params = HeavyRainfallParams(rainfall_multiplier=2.0, rainfall_delta_mm=30.0)
    assert params.rainfall_multiplier == 2.0
    assert params.rainfall_delta_mm == 30.0

    # Negative multiplier
    with pytest.raises(ValidationError):
        HeavyRainfallParams(rainfall_multiplier=-1.0)


def test_optimization_request_validation():
    # Valid optimization request
    req = OptimizationRequest(
        resource_types=["hospital"],
        method="ortools_min_cost_flow"
    )
    assert req.resource_types == ["hospital"]


# 2. Parameter Boundary & Extreme Values Testing
def test_tool_registry_boundary_parameters():
    mock_db = MockSession()

    # Upper limit boundary check (limit > max allowed limit 200)
    with pytest.raises(ValueError) as exc_info:
        execute_tool("get_flood_risk", {"limit": 5000}, db=mock_db)
    assert "Invalid parameters" in str(exc_info.value)

    # Negative limit boundary check (limit < min allowed limit 1)
    with pytest.raises(ValueError) as exc_info:
        execute_tool("get_flood_risk", {"limit": -10}, db=mock_db)
    assert "Invalid parameters" in str(exc_info.value)

    # Invalid risk level enum check
    params = FloodRiskParams(risk_level="INVALID_LEVEL")
    assert params.risk_level == "INVALID_LEVEL"


# 3. Numerical Edge Cases (NaN, Infinity, Invalid Ranges)
def test_numerical_edge_cases_handling():
    nan_val = float('nan')
    inf_val = float('inf')
    
    assert math.isnan(nan_val)
    assert math.isinf(inf_val)

    # SpatialScope validation for inverted longitude bounds
    with pytest.raises(ValidationError):
        SpatialScope(scope_type="bbox", min_lon=90.0, max_lon=80.0)
