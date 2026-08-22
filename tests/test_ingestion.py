import pytest
from shapely.geometry import Polygon, MultiPolygon
from pipelines.ingest_wards import validate_and_normalize_feature

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
