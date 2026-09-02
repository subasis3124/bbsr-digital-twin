import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_get_dashboard_summary():
    """
    Test the GET /api/v1/dashboard/summary endpoint.
    Verifies that city KPIs, spatial counts, risk summaries, and provenance warnings are returned.
    """
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["engine_name"] == "Bhubaneswar Digital Twin Command Center"
    assert "timestamp" in data
    assert "system_status" in data
    assert "provenance_status" in data
    assert "is_synthetic" in data
    assert "scientific_validation_warning" in data

    # Infrastructure metrics
    infra = data["infrastructure"]
    assert "wards" in infra
    assert "grid_cells" in infra
    assert "roads" in infra
    assert "hospitals" in infra
    assert "police_stations" in infra
    assert "fire_stations" in infra

    # Flood risk metrics
    flood = data["flood_risk"]
    assert "total_evaluated_cells" in flood
    assert "by_category" in flood
    assert "high_risk_cells_count" in flood

    # Traffic metrics
    traffic = data["traffic"]
    assert "monitored_segments" in traffic
    assert "average_speed_kmh" in traffic

    # Air Quality metrics
    aq = data["air_quality"]
    assert "forecast_count" in aq
    assert "average_pollutant_value" in aq

    # Simulation & Optimization stats
    assert "simulations" in data
    assert "optimization" in data
