import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db
from backend.app.ai.schemas import (
    AIQueryRequest, AIResponse, AIIntentEnum, AIResponseTypeEnum,
    AIToolCall, AIToolResult, AIMapAction, AIProvenance
)
from backend.app.ai.intents import classify_intent
from backend.app.ai.tools import TOOL_REGISTRY, execute_tool, get_registered_tool_names
from backend.app.ai.providers import MockAIProvider, OpenAIProvider
from backend.app.ai.pipeline import AIOrchestrator, MAX_TOOL_CALLS


class MockQuery:
    def __init__(self, model):
        self.model = model
        self.items = []

    def all(self):
        return self.items

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

    def first(self):
        return None

    def count(self):
        return len(self.items)

    def scalar(self):
        return 0


class MockSession:
    def __init__(self):
        self.added = []

    def query(self, *args, **kwargs):
        model = args[0] if args else None
        return MockQuery(model)

    def add(self, obj):
        self.added.append(obj)

    def add_all(self, objs):
        self.added.extend(objs)

    def commit(self):
        pass

    def refresh(self, obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = 1

    def close(self):
        pass


@pytest.fixture(scope="function")
def test_db():
    db = MockSession()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# 1. Intent Parsing Tests
def test_intent_classification():
    assert classify_intent("Show me high flood risk areas") == AIIntentEnum.FLOOD_RISK_QUERY
    assert classify_intent("What is the traffic forecast for Janpath?") == AIIntentEnum.TRAFFIC_QUERY
    assert classify_intent("Show air quality and AQI readings") == AIIntentEnum.AIR_QUALITY_QUERY
    assert classify_intent("Show hospital bed capacity") == AIIntentEnum.RESOURCE_QUERY
    assert classify_intent("Simulate heavy rainfall in Ward 20") == AIIntentEnum.SIMULATION_QUERY
    assert classify_intent("Optimize emergency resource allocation") == AIIntentEnum.OPTIMIZATION_QUERY
    assert classify_intent("Why is this cell classified as high risk?") == AIIntentEnum.EXPLANATION_QUERY
    assert classify_intent("System status and KPI summary") == AIIntentEnum.SYSTEM_STATUS_QUERY
    assert classify_intent("random gibberish xyz123") == AIIntentEnum.UNKNOWN


def test_traffic_congestion_intents():
    assert classify_intent("which area is most congested") == AIIntentEnum.TRAFFIC_QUERY
    assert classify_intent("which roads are congested") == AIIntentEnum.TRAFFIC_QUERY
    assert classify_intent("where is traffic congestion highest") == AIIntentEnum.TRAFFIC_QUERY


def test_execute_get_air_quality_without_attribute_error():
    class MockAirQualityPrediction:
        station_name = "Bhubaneswar Central"
        pollutant = "PM25"
        predicted_value = 45.2
        aqi_sub_index = 60
        horizon_hours = 6
        is_synthetic = True

    class AirQualityMockQuery(MockQuery):
        def __init__(self):
            super().__init__(None)
            self.items = [MockAirQualityPrediction()]

    class AirQualityMockSession(MockSession):
        def query(self, *args, **kwargs):
            return AirQualityMockQuery()

    session = AirQualityMockSession()
    res = execute_tool("get_air_quality", {"limit": 10}, db=session)
    assert res["count"] == 1
    assert res["stations"][0]["station_name"] == "Bhubaneswar Central"
    assert res["stations"][0]["aqi_sub_index"] == 60
    assert res["stations"][0]["horizon_hours"] == 6


# 2. Tool Registry Tests
def test_tool_registry():
    registered_tools = get_registered_tool_names()
    assert "get_flood_risk" in registered_tools
    assert "get_gnn_traffic" in registered_tools
    assert "get_air_quality" in registered_tools
    assert "run_simulation" in registered_tools
    assert "run_emergency_optimization" in registered_tools
    assert "get_dashboard_summary" in registered_tools


# 3. Schema Validation & Parameter Limits
def test_schema_validation(test_db):
    # Valid parameters
    result = execute_tool("get_hospitals", {"limit": 10}, db=test_db)
    assert result["count"] == 0 or isinstance(result["count"], int)

    # Invalid parameter type / out of bounds
    with pytest.raises(ValueError) as exc_info:
        execute_tool("get_flood_risk", {"limit": 1000}, db=test_db)  # Limit max is 200
    assert "Invalid parameters" in str(exc_info.value)


# 4. Invalid / Unknown Tool Call Rejection
def test_unknown_tool_rejection(test_db):
    with pytest.raises(ValueError) as exc_info:
        execute_tool("execute_arbitrary_sql", {"sql": "SELECT * FROM users"}, db=test_db)
    assert "not registered" in str(exc_info.value)


# 5. Malicious Request Rejection
def test_malicious_request_prevention(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="DROP TABLE wards; SELECT * FROM credentials;")
    res = provider.process_query(req, db=test_db)
    
    assert res.intent == AIIntentEnum.UNKNOWN
    assert "don't have validated data" in res.answer or "registered tool" in res.answer
    assert len(res.tool_calls) == 0


# 6. Flood Query Execution
def test_flood_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Show me high flood-risk areas.")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.FLOOD_RISK_QUERY
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "get_flood_risk"
    assert any(ma.action == "set_layer_visibility" and ma.layer == "floodRisk" for ma in res.map_actions)
    assert res.provenance.is_synthetic is True


# 7. Traffic Query Execution
def test_traffic_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="What is the traffic speed forecast?")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.TRAFFIC_QUERY
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "get_gnn_traffic"
    assert any(ma.layer == "trafficForecast" for ma in res.map_actions)


# 8. Air Quality Query Execution
def test_air_quality_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Show air quality and PM2.5 levels")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.AIR_QUALITY_QUERY
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "get_air_quality"
    assert any(ma.layer == "airQuality" for ma in res.map_actions)


# 9. Emergency Resource Query Execution
def test_resource_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Which hospitals are available in Ward 20?")
    res = provider.process_query(req, db=test_db)

    assert res.intent in (AIIntentEnum.RESOURCE_QUERY, AIIntentEnum.INFRASTRUCTURE_QUERY)
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "get_hospitals"


# 10. City State Query Execution
def test_city_state_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Show overall city state summary")
    res = provider.process_query(req, db=test_db)

    assert res.intent in (AIIntentEnum.CITY_STATE_QUERY, AIIntentEnum.SYSTEM_STATUS_QUERY)
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "get_dashboard_summary"


# 11. Simulation Command Execution
def test_simulation_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Simulate heavy rainfall scenario")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.SIMULATION_QUERY
    assert res.response_type == AIResponseTypeEnum.SIMULATION_RESULT
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "run_simulation"
    assert "counterfactual" in res.answer.lower() or "executed" in res.answer.lower()


# 12. Optimization Command Execution
def test_optimization_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Run emergency allocation for hospitals")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.OPTIMIZATION_QUERY
    assert res.response_type == AIResponseTypeEnum.OPTIMIZATION_RESULT
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].tool == "run_emergency_optimization"
    assert any(ma.layer == "allocations" for ma in res.map_actions)


# 13. Spatial Context & Resolution
def test_spatial_context_query(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="Show flood risk", spatial_context="ward:20")
    res = provider.process_query(req, db=test_db)

    assert res.tool_calls[0].parameters.get("ward_id") == 20


# 14. Provenance & Synthetic Data Warning Propagation
def test_provenance_propagation(test_db):
    orchestrator = AIOrchestrator(provider=MockAIProvider())
    req = AIQueryRequest(query="Show high flood risk areas")
    res = orchestrator.process_natural_language_query(req, db=test_db)

    assert res.provenance is not None
    assert res.provenance.is_synthetic is True
    assert len(res.warnings) > 0
    assert "synthetic" in res.warnings[0].lower()


# 15. Unsupported / Hallucination Safeguard Test
def test_unsupported_question(test_db):
    provider = MockAIProvider()
    req = AIQueryRequest(query="What will the stock market do tomorrow?")
    res = provider.process_query(req, db=test_db)

    assert res.intent == AIIntentEnum.UNKNOWN
    assert "don't have validated data" in res.answer or "registered tool" in res.answer
    assert len(res.tool_calls) == 0


# 16. Tool-Call Limit Protection Test
def test_tool_call_limit_enforcement(test_db):
    class MultiToolProvider(MockAIProvider):
        def process_query(self, req: AIQueryRequest, db: MockSession) -> AIResponse:
            res = super().process_query(req, db)
            res.tool_calls = [AIToolCall(tool="get_hospitals", parameters={}) for _ in range(5)]
            res.tool_results = [AIToolResult(tool="get_hospitals", success=True) for _ in range(5)]
            return res

    orchestrator = AIOrchestrator(provider=MultiToolProvider())
    req = AIQueryRequest(query="Test multi tool limit")
    res = orchestrator.process_natural_language_query(req, db=test_db)

    assert len(res.tool_calls) == MAX_TOOL_CALLS
    assert len(res.tool_results) == MAX_TOOL_CALLS
    assert any("capped" in w for w in res.warnings)


# 17. FastAPI Router API Endpoint Test (`POST /api/v1/ai/query`)
def test_ai_query_api_endpoint(client):
    payload = {
        "query": "Show me high flood-risk areas.",
        "spatial_context": "ward:20"
    }
    response = client.post("/api/v1/ai/query", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "Show me high flood-risk areas."
    assert data["intent"] == "FLOOD_RISK_QUERY"
    assert "answer" in data
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["tool"] == "get_flood_risk"
    assert data["provenance"]["is_synthetic"] is True


def test_ai_tools_api_endpoint(client):
    response = client.get("/api/v1/ai/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tools"] > 0
    assert any(t["name"] == "get_flood_risk" for t in data["tools"])


def test_ai_intents_api_endpoint(client):
    response = client.get("/api/v1/ai/intents")
    assert response.status_code == 200
    data = response.json()
    assert "FLOOD_RISK_QUERY" in data["intents"]
