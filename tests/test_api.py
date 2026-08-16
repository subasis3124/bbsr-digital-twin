import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db

client = TestClient(app)

# ==========================================
# Mock Database Session for API Testing
# ==========================================

class MockQuery:
    def __init__(self, model):
        self.model = model

    def all(self):
        return []

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

class MockSession:
    def query(self, model):
        return MockQuery(model)

    def execute(self, statement):
        # Force exception to simulate database/PostGIS not initialized or down
        raise Exception("PostgreSQL connection refused")

    def close(self):
        pass

def override_get_db():
    db = MockSession()
    try:
        yield db
    finally:
        db.close()

# Override FastAPI get_db dependency injection with MockSession
app.dependency_overrides[get_db] = override_get_db


def test_read_root():
    """
    Verifies that the API home route is online and returns API info.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to BBSR Digital Twin API" in response.json()["message"]


def test_health_check_unhealthy():
    """
    Verifies that when PostgreSQL/PostGIS is unreachable,
    the health endpoint correctly returns 503 Service Unavailable.
    """
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()["detail"]
    assert data["status"] == "unhealthy"
    assert data["database"] == "disconnected"
    assert data["postgis"] == "unavailable"


def test_get_cities_empty():
    """
    Verifies that fetching cities returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/cities")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_wards_empty():
    """
    Verifies that fetching wards returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/wards")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_ward_by_id_not_found():
    """
    Verifies that querying a non-existent ward ID returns 404 Not Found.
    """
    response = client.get("/api/v1/wards/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
