import pytest
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from pipelines.ingest_wards import validate_and_normalize_feature
from pipelines.ingest_roads import parse_lanes, parse_maxspeed, parse_oneway
from pipelines.ingest_buildings import parse_height, parse_levels
from pipelines.ingest_hospitals import parse_beds, parse_geometry
from pipelines.ingest_schools import parse_geometry as parse_school_geometry
from pipelines.ingest_police import parse_geometry as parse_police_geometry
from pipelines.ingest_bus_stops import parse_geometry as parse_bus_stop_geometry
from pipelines.ingest_water_bodies import parse_geometry as parse_water_body_geometry
from pipelines.ingest_bus_routes import parse_geometry as parse_bus_route_geometry





def test_validate_and_normalize_valid_polygon():
    """
    Checks that a valid feature with a Polygon geometry is successfully validated
    and correctly normalized to a MultiPolygon geometry.
    """
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[85.0, 20.0], [85.1, 20.0], [85.1, 20.1], [85.0, 20.1], [85.0, 20.0]]]
        },
        "properties": {
            "wardno": "W9",
            "nameofthec": "Suryakanti Jena",
            "totalwardp": 13932
        }
    }
    
    ward_number, name, population_est, geom_shape = validate_and_normalize_feature(feature)
    
    assert ward_number == 9
    assert name == "Suryakanti Jena"
    assert population_est == 13932
    assert isinstance(geom_shape, MultiPolygon)
    assert len(geom_shape.geoms) == 1

def test_validate_and_normalize_invalid_wardno():
    """
    Checks that features with invalid or missing wardno identifiers throw a ValueError.
    """
    # 1. Non-W prefix
    feature_bad_prefix = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {"wardno": "9", "totalwardp": 100}
    }
    with pytest.raises(ValueError, match="invalid wardno key"):
        validate_and_normalize_feature(feature_bad_prefix)

    # 2. Non-numeric portion
    feature_bad_numeric = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {"wardno": "Wabc", "totalwardp": 100}
    }
    with pytest.raises(ValueError, match="portion is not numeric"):
        validate_and_normalize_feature(feature_bad_numeric)

def test_validate_and_normalize_invalid_population():
    """
    Checks that missing or non-integer population counts throw a ValueError.
    """
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[85.0, 20.0], [85.1, 20.0], [85.1, 20.1], [85.0, 20.1], [85.0, 20.0]]]
        },
        "properties": {
            "wardno": "W9",
            "totalwardp": "not_an_int"
        }
    }
    with pytest.raises(ValueError, match="Population value is not a valid integer"):
        validate_and_normalize_feature(feature)

def test_parse_lanes():
    """
    Verifies that various format lanes values are parsed correctly.
    """
    assert parse_lanes(None) is None
    assert parse_lanes(2) == 2
    assert parse_lanes("3") == 3
    assert parse_lanes("2;3") == 2
    assert parse_lanes("abc") is None

def test_parse_maxspeed():
    """
    Verifies that maxspeed values with units are cleaned and parsed correctly.
    """
    assert parse_maxspeed(None) is None
    assert parse_maxspeed(50) == 50
    assert parse_maxspeed("60") == 60
    assert parse_maxspeed("40 km/h") == 40
    assert parse_maxspeed("30 mph") == 48  # 30 * 1.609 = 48.27 -> 48
    assert parse_maxspeed("urban;40") == 40
    assert parse_maxspeed("invalid_speed") is None

def test_parse_oneway():
    """
    Verifies that oneway values are converted correctly to booleans.
    """
    assert parse_oneway(None) is False
    assert parse_oneway(True) is True
    assert parse_oneway("yes") is True
    assert parse_oneway("1") is True
    assert parse_oneway("true") is True
    assert parse_oneway("no") is False
    assert parse_oneway("0") is False

def test_parse_height():
    """
    Verifies that building heights are parsed correctly.
    """
    assert parse_height(None) is None
    assert parse_height(15.5) == 15.5
    assert parse_height("12") == 12.0
    assert parse_height("18.5 m") == 18.5
    assert parse_height("20 meters") == 20.0
    assert parse_height("invalid_height") is None

def test_parse_levels():
    """
    Verifies that building levels are parsed correctly.
    """
    assert parse_levels(None) is None
    assert parse_levels(3) == 3
    assert parse_levels("4") == 4
    assert parse_levels("ground+2") == 2  # Extract first digit sequence found
    assert parse_levels("invalid_levels") is None

def test_parse_beds():
    """
    Verifies that hospital bed capacity numbers are parsed correctly.
    """
    assert parse_beds({}) is None
    assert parse_beds({"beds": 50}) == 50
    assert parse_beds({"beds": "100"}) == 100
    assert parse_beds({"healthcare:beds": "250"}) == 250
    assert parse_beds({"beds": "approx 30 beds"}) == 30
    assert parse_beds({"beds": "none"}) is None

def test_parse_geometry():
    """
    Verifies that OSM geometries (Nodes, Ways) are parsed and converted to Point.
    """
    # 1. Test Node (Point)
    node = {"type": "node", "id": 1, "lat": 20.25, "lon": 85.83}
    pt = parse_geometry(node)
    assert isinstance(pt, Point)
    assert pt.x == 85.83
    assert pt.y == 20.25

    # 2. Test Way (Polygon Centroid)
    way = {
        "type": "way",
        "id": 2,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8},
            {"lat": 20.3, "lon": 85.9},
            {"lat": 20.2, "lon": 85.9},
            {"lat": 20.2, "lon": 85.8}
        ]
    }
    pt2 = parse_geometry(way)
    assert isinstance(pt2, Point)
    assert pt2.x == pytest.approx(85.85)
    assert pt2.y == pytest.approx(20.25)


def test_parse_school_geometry():
    # Test Node (Point)
    node = {"type": "node", "id": 10, "lat": 20.30, "lon": 85.86}
    pt = parse_school_geometry(node)
    assert isinstance(pt, Point)
    assert pt.x == 85.86
    assert pt.y == 20.30

    # Test Way (Centroid)
    way = {
        "type": "way",
        "id": 11,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8},
            {"lat": 20.3, "lon": 85.9},
            {"lat": 20.2, "lon": 85.9},
            {"lat": 20.2, "lon": 85.8}
        ]
    }
    pt2 = parse_school_geometry(way)
    assert isinstance(pt2, Point)
    assert pt2.x == pytest.approx(85.85)
    assert pt2.y == pytest.approx(20.25)


def test_parse_safety_geometry():
    # Test Node (Point)
    node = {"type": "node", "id": 20, "lat": 20.32, "lon": 85.88}
    pt = parse_police_geometry(node)
    assert isinstance(pt, Point)
    assert pt.x == 85.88
    assert pt.y == 20.32

    # Test Way (Centroid)
    way = {
        "type": "way",
        "id": 21,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8},
            {"lat": 20.3, "lon": 85.9},
            {"lat": 20.2, "lon": 85.9},
            {"lat": 20.2, "lon": 85.8}
        ]
    }
    pt2 = parse_police_geometry(way)
    assert isinstance(pt2, Point)
    assert pt2.x == pytest.approx(85.85)
    assert pt2.y == pytest.approx(20.25)


def test_parse_bus_stop_geometry():
    # Test Node (Point)
    node = {"type": "node", "id": 30, "lat": 20.35, "lon": 85.90}
    pt = parse_bus_stop_geometry(node)
    assert isinstance(pt, Point)
    assert pt.x == 85.90
    assert pt.y == 20.35

    # Test Way (Centroid)
    way = {
        "type": "way",
        "id": 31,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8},
            {"lat": 20.3, "lon": 85.9},
            {"lat": 20.2, "lon": 85.9},
            {"lat": 20.2, "lon": 85.8}
        ]
    }
    pt2 = parse_bus_stop_geometry(way)
    assert isinstance(pt2, Point)
    assert pt2.x == pytest.approx(85.85)
    assert pt2.y == pytest.approx(20.25)


def test_parse_water_body_geometry():
    # Test Way (Polygon)
    way = {
        "type": "way",
        "id": 40,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8},
            {"lat": 20.3, "lon": 85.9},
            {"lat": 20.2, "lon": 85.9},
            {"lat": 20.2, "lon": 85.8}
        ]
    }
    poly = parse_water_body_geometry(way)
    assert isinstance(poly, Polygon)
    assert poly.exterior.coords[0] == (85.8, 20.2)
    assert poly.exterior.coords[2] == (85.9, 20.3)


def test_parse_water_body_geometry_relation():
    # Test Relation (Multiple Polygons, largest is resolved)
    relation = {
        "type": "relation",
        "id": 41,
        "members": [
            {
                "type": "way",
                "ref": 100,
                "role": "outer",
                "geometry": [
                    {"lat": 20.2, "lon": 85.8},
                    {"lat": 20.3, "lon": 85.8},
                    {"lat": 20.3, "lon": 85.9},
                    {"lat": 20.2, "lon": 85.9},
                    {"lat": 20.2, "lon": 85.8}
                ]
            },
            {
                "type": "way",
                "ref": 101,
                "role": "outer",
                "geometry": [
                    {"lat": 20.2, "lon": 85.8},
                    {"lat": 20.22, "lon": 85.8},
                    {"lat": 20.22, "lon": 85.82},
                    {"lat": 20.2, "lon": 85.82},
                    {"lat": 20.2, "lon": 85.8}
                ]
            }
        ]
    }
    poly = parse_water_body_geometry(relation)
    assert isinstance(poly, Polygon)
    # The first polygon has area ~0.01 deg^2, the second is ~0.0004 deg^2. Major one should be chosen.
    assert poly.area > 0.005
    assert poly.exterior.coords[0] == (85.8, 20.2)
    assert poly.exterior.coords[2] == (85.9, 20.3)


def test_parse_water_body_geometry_invalid():
    # Invalid coordinates (less than 3)
    way_few_coords = {
        "type": "way",
        "id": 42,
        "geometry": [
            {"lat": 20.2, "lon": 85.8},
            {"lat": 20.3, "lon": 85.8}
        ]
    }
    assert parse_water_body_geometry(way_few_coords) is None

    # Invalid type
    node = {
        "type": "node",
        "id": 43,
        "lat": 20.2,
        "lon": 85.8
    }
    assert parse_water_body_geometry(node) is None


def test_parse_bus_route_geometry():
    # Test valid relation with member ways
    relation = {
        "type": "relation",
        "id": 50,
        "members": [
            {
                "type": "way",
                "ref": 300,
                "geometry": [
                    {"lat": 20.2, "lon": 85.8},
                    {"lat": 20.3, "lon": 85.8}
                ]
            },
            {
                "type": "way",
                "ref": 301,
                "geometry": [
                    {"lat": 20.3, "lon": 85.8},
                    {"lat": 20.3, "lon": 85.9}
                ]
            }
        ]
    }
    line = parse_bus_route_geometry(relation)
    assert isinstance(line, LineString)
    assert list(line.coords) == [(85.8, 20.2), (85.8, 20.3), (85.9, 20.3)]


def test_parse_bus_route_geometry_invalid():
    # Invalid coordinates (less than 2)
    relation_bad = {
        "type": "relation",
        "id": 51,
        "members": [
            {
                "type": "way",
                "ref": 303,
                "geometry": [
                    {"lat": 20.2, "lon": 85.8}
                ]
            }
        ]
    }
    assert parse_bus_route_geometry(relation_bad) is None

    # Invalid type
    node = {
        "type": "node",
        "id": 52,
        "lat": 20.2,
        "lon": 85.8
    }
    assert parse_bus_route_geometry(node) is None
