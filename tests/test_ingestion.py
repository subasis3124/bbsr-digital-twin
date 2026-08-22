import pytest
from shapely.geometry import Polygon, MultiPolygon
from pipelines.ingest_wards import validate_and_normalize_feature
from pipelines.ingest_roads import parse_lanes, parse_maxspeed, parse_oneway

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
