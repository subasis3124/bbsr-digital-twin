import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, MultiPolygon
from geoalchemy2.shape import from_shape
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import WaterBody, Ward

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

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
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


def test_get_roads_empty():
    """
    Verifies that fetching roads returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/roads")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_road_by_id_not_found():
    """
    Verifies that querying a non-existent road ID returns 404 Not Found.
    """
    response = client.get("/api/v1/roads/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_buildings_empty():
    """
    Verifies that fetching buildings returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/buildings")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_building_by_id_not_found():
    """
    Verifies that querying a non-existent building ID returns 404 Not Found.
    """
    response = client.get("/api/v1/buildings/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_hospitals_empty():
    """
    Verifies that fetching hospitals returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/hospitals")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_hospital_by_id_not_found():
    """
    Verifies that querying a non-existent hospital ID returns 404 Not Found.
    """
    response = client.get("/api/v1/hospitals/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_schools_empty():
    """
    Verifies that fetching schools returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/schools")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_school_by_id_not_found():
    """
    Verifies that querying a non-existent school ID returns 404 Not Found.
    """
    response = client.get("/api/v1/schools/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_police_empty():
    """
    Verifies that fetching police stations returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/police")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_police_by_id_not_found():
    """
    Verifies that querying a non-existent police station ID returns 404 Not Found.
    """
    response = client.get("/api/v1/police/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_fire_stations_empty():
    """
    Verifies that fetching fire stations returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/fire-stations")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_fire_station_by_id_not_found():
    """
    Verifies that querying a non-existent fire station ID returns 404 Not Found.
    """
    response = client.get("/api/v1/fire-stations/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_bus_stops_empty():
    """
    Verifies that fetching bus stops returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/bus-stops")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_bus_stop_by_id_not_found():
    """
    Verifies that querying a non-existent bus stop ID returns 404 Not Found.
    """
    response = client.get("/api/v1/bus-stops/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_water_bodies_empty():
    """
    Verifies that fetching water bodies returns an empty GeoJSON FeatureCollection when no records exist.
    """
    response = client.get("/api/v1/water-bodies")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


def test_get_water_body_by_id_not_found():
    """
    Verifies that querying a non-existent water body ID returns 404 Not Found.
    """
    response = client.get("/api/v1/water-bodies/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_water_bodies_api_rich_scenarios():
    # 1. Create mock data
    poly1 = Polygon([(85.8, 20.2), (85.8, 20.3), (85.9, 20.3), (85.9, 20.2), (85.8, 20.2)])
    poly2 = Polygon([(85.75, 20.21), (85.75, 20.25), (85.78, 20.25), (85.78, 20.21), (85.75, 20.21)])
    
    mock_wb1 = WaterBody(
        id=1,
        osm_id=1001,
        name="Bindusagar Lake",
        water_type="lake",
        geom=from_shape(poly1, srid=4326)
    )
    mock_wb2 = WaterBody(
        id=2,
        osm_id=1002,
        name="Daya Canal",
        water_type="canal",
        geom=from_shape(poly2, srid=4326)
    )
    
    mock_ward = Ward(
        id=5,
        ward_number=5,
        name="Old Town",
        geom=from_shape(MultiPolygon([poly1]), srid=4326)
    )
    
    # 2. Define custom MockQuery for filtering and pagination simulation
    class WaterBodyMockQuery:
        def __init__(self, data, model=WaterBody):
            self.data = data
            self.model = model
            self._offset = 0
            self._limit = None

        def filter(self, *args, **kwargs):
            filtered = list(self.data)
            for arg in args:
                try:
                    col_name = arg.left.name.lower()
                    val = arg.right.value
                    if col_name == 'name':
                        clean_val = str(val).replace('%', '').lower()
                        filtered = [x for x in filtered if clean_val in (x.name or "").lower()]
                    elif col_name == 'water_type':
                        filtered = [x for x in filtered if x.water_type == val]
                    elif col_name == 'id':
                        filtered = [x for x in filtered if x.id == val]
                except Exception:
                    arg_str = str(arg).lower()
                    if "intersects" in arg_str or "ward" in arg_str or "geom" in arg_str:
                        filtered = [x for x in filtered if x.id == 1]
            return WaterBodyMockQuery(filtered, self.model)

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

    class WardMockQuery:
        def __init__(self, data):
            self.data = data

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.data[0] if self.data else None

    class RichMockSession:
        def query(self, model):
            if model == WaterBody:
                return WaterBodyMockQuery([mock_wb1, mock_wb2], WaterBody)
            elif model == Ward:
                return WardMockQuery([mock_ward])
            return MockQuery(model)

        def close(self):
            pass

    def rich_get_db():
        db = RichMockSession()
        try:
            yield db
        finally:
            db.close()

    # Apply override
    app.dependency_overrides[get_db] = rich_get_db
    
    try:
        # A. Test collection API returning both items
        res = client.get("/api/v1/water-bodies")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2
        names = [f["properties"]["name"] for f in data["features"]]
        assert "Bindusagar Lake" in names
        assert "Daya Canal" in names

        # B. Test Pagination: limit=1
        res = client.get("/api/v1/water-bodies?limit=1")
        assert res.status_code == 200
        data = res.json()
        assert len(data["features"]) == 1

        # C. Test Pagination: offset=1
        res = client.get("/api/v1/water-bodies?offset=1")
        assert res.status_code == 200
        data = res.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["name"] == "Daya Canal"

        # D. Test Name filter matching "Lake"
        res = client.get("/api/v1/water-bodies?name=Lake")
        assert res.status_code == 200
        data = res.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["name"] == "Bindusagar Lake"

        # E. Test Water Type filter
        res = client.get("/api/v1/water-bodies?water_type=canal")
        assert res.status_code == 200
        data = res.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["name"] == "Daya Canal"

        # F. Test Ward ID spatial filter
        res = client.get("/api/v1/water-bodies?ward_id=5")
        assert res.status_code == 200
        data = res.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["name"] == "Bindusagar Lake"

        # G. Test Single Water Body Endpoint
        res = client.get("/api/v1/water-bodies/1")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "Feature"
        assert data["properties"]["name"] == "Bindusagar Lake"

        res = client.get("/api/v1/water-bodies/2")
        assert res.status_code == 200
        data = res.json()
        assert data["properties"]["name"] == "Daya Canal"

    finally:
        # Restore mock session to empty
        app.dependency_overrides[get_db] = override_get_db

