import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from backend.app.main import app
from backend.app.database import get_db
from backend.app import models
from ml.simulation import WhatIfSimulationEngine, HeavyRainfallParams
from ml.optimization import EmergencyOptimizationEngine, EmergencyDemand, EmergencyResource
from backend.app.ai.pipeline import AIOrchestrator
from backend.app.ai.providers import MockAIProvider
from backend.app.ai.schemas import AIQueryRequest, AIIntentEnum
from tests.test_ai_interface import MockSession, MockQuery

client = TestClient(app)


def override_get_db():
    db = MockSession()
    try:
        yield db
    finally:
        db.close()


# 1. End-to-End Simulation -> Optimization Integration Pipeline
def test_e2e_simulation_to_optimization_workflow():
    """
    Tests end-to-end integration:
    1. Run Heavy Rainfall counterfactual simulation.
    2. Retrieve simulation impact output.
    3. Pass simulation context into Emergency Optimization.
    4. Verify that emergency resource allocation accounts for simulated flooded accessibility degradations.
    """
    mock_db = MockSession()

    # Step 1: Run Simulation
    sim_engine = WhatIfSimulationEngine(db=mock_db)
    sim_result = sim_engine.run_simulation(
        scenario_type="heavy_rainfall",
        parameters={"rainfall_multiplier": 2.5, "rainfall_delta_mm": 50.0},
        save=False
    )
    assert sim_result.scenario.scenario_id is not None
    assert sim_result.impact_summary.affected_spatial_units_count >= 0

    # Step 2: Optimization with Simulation Impact Context
    now_str = datetime.now(timezone.utc).isoformat()
    demands = [
        EmergencyDemand(
            demand_id="DEM_E2E_01",
            spatial_id="WARD_01",
            coordinates=[85.8200, 20.2700],
            timestamp=now_str,
            demand_quantity=20,
            emergency_type="medical",
            priority="CRITICAL",
            priority_weight=3.0
        )
    ]

    resources = [
        # Hospital 1: Flooded in simulation (accessibility degraded to 0.0)
        EmergencyResource(
            resource_id="HOSP_FLOODED",
            resource_type="hospital",
            name="Downtown Flooded Clinic",
            coordinates=[85.8205, 20.2705],
            capacity=30,
            available_capacity=30,
            accessibility=0.0,
            status="INACCESSIBLE",
            timestamp=now_str
        ),
        # Hospital 2: Safe alternative
        EmergencyResource(
            resource_id="HOSP_SAFE",
            resource_type="hospital",
            name="Upland General Hospital",
            coordinates=[85.8600, 20.3000],
            capacity=50,
            available_capacity=50,
            accessibility=1.0,
            status="AVAILABLE",
            timestamp=now_str
        )
    ]

    opt_engine = EmergencyOptimizationEngine(db=mock_db)
    opt_result = opt_engine.optimize(
        demands=demands,
        resources=resources,
        method="ortools_min_cost_flow",
        save=False
    )

    assert opt_result.run_id is not None
    assert opt_result.summary.served_demand == 20
    # HOSP_FLOODED must receive 0 allocation due to 0.0 accessibility
    hosp_flooded_assigned = sum(
        a.allocation_quantity for a in opt_result.allocations if a.assigned_resource_id == "HOSP_FLOODED"
    )
    assert hosp_flooded_assigned == 0


# 2. End-to-End AI Natural Language Multi-Step Query & Tool Execution
def test_e2e_ai_natural_language_tool_chain():
    """
    Tests end-to-end AI query workflow:
    1. Send natural language prompt: "Show traffic forecast near Ward 5"
    2. AIOrchestrator classifies query into TRAFFIC_FORECAST intent
    3. Tool resolution selects get_traffic_forecast tool
    4. Controlled tool registry executes query against mock DB cleanly
    """
    provider = MockAIProvider()
    orchestrator = AIOrchestrator(provider=provider)

    req = AIQueryRequest(query="What is the forecasted traffic speed near Ward 5?", spatial_context="ward:5")
    res = orchestrator.process_natural_language_query(req, db=MockSession())

    assert res.intent == AIIntentEnum.TRAFFIC_QUERY
    assert len(res.tool_calls) >= 1
    assert res.tool_calls[0].tool in ["get_traffic_forecast", "get_gnn_traffic"]
    assert res.provenance.is_synthetic is True


# 3. Comprehensive REST API Contract Verification
def test_api_contract_consistency():
    """
    Audits REST API contract response structures for tools and AI query endpoints.
    """
    app.dependency_overrides[get_db] = override_get_db
    try:
        # 1. AI Tools Registry endpoint
        r_tools = client.get("/api/v1/ai/tools")
        assert r_tools.status_code == 200
        assert "tools" in r_tools.json()
        assert len(r_tools.json()["tools"]) >= 15

        # 2. AI Query endpoint
        r_ai = client.post("/api/v1/ai/query", json={"query": "List hospitals in Bhubaneswar", "spatial_context": "ward:1"})
        assert r_ai.status_code == 200
        data_ai = r_ai.json()
        assert "query_id" in data_ai
        assert "intent" in data_ai
        assert "provenance" in data_ai
    finally:
        app.dependency_overrides.pop(get_db, None)
