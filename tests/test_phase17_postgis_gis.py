import pytest
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from geoalchemy2.shape import from_shape, to_shape

from backend.app import models
from backend.app.config import settings


# 1. Database Table Structure & Geometry Column Audit
def test_postgis_table_and_geometry_structures():
    """
    Verifies that database model classes exist and have correct spatial / key fields.
    """
    spatial_tables = [
        (models.City, ["id", "name", "geom"]),
        (models.Ward, ["id", "ward_number", "geom"]),
        (models.Road, ["id", "osm_id", "geom"]),
        (models.Building, ["id", "building_type", "geom"]),
        (models.Hospital, ["id", "name", "geom"]),
        (models.School, ["id", "name", "geom"]),
        (models.PoliceStation, ["id", "name", "geom"]),
        (models.FireStation, ["id", "name", "geom"]),
        (models.BusStop, ["id", "name", "geom"]),
        (models.BusRoute, ["id", "route_name", "geom"]),
        (models.WaterBody, ["id", "name", "geom"]),
        (models.Prediction, ["id", "cell_id", "predicted_probability"]),
        (models.Traffic, ["id", "road_id", "observed_speed"]),
        (models.AirQualityPrediction, ["id", "station_name", "predicted_value"]),
        (models.GNNTrafficPrediction, ["id", "road_id", "predicted_speed"]),
        (models.CityStateSnapshot, ["id", "state_timestamp", "payload"]),
        (models.SimulationRun, ["id", "scenario_type", "impact_summary"]),
        (models.OptimizationRun, ["id", "run_id", "allocation_results"])
    ]

    for model_cls, expected_attrs in spatial_tables:
        for attr in expected_attrs:
            assert hasattr(model_cls, attr), f"{model_cls.__name__} missing attribute '{attr}'"


# 2. GIS Correctness & Spatial Calculations
def test_gis_spatial_ordering_and_containment():
    """
    Tests lat/lon ordering, SRID 4326 geometry creation, point containment, and bounding box logic.
    """
    # Bhubaneswar Center Point: Lon 85.83, Lat 20.27
    lon, lat = 85.83, 20.27
    point_bb = Point(lon, lat)

    # Convert to GeoAlchemy2 shape with SRID 4326
    spatial_element = from_shape(point_bb, srid=4326)
    assert spatial_element.srid == 4326

    # Polygon enclosing point
    poly = Polygon([
        (85.80, 20.20),
        (85.90, 20.20),
        (85.90, 20.30),
        (85.80, 20.30),
        (85.80, 20.20)
    ])

    assert poly.contains(point_bb)

    # Point outside polygon
    outside_point = Point(86.00, 20.50)
    assert not poly.contains(outside_point)


def test_gis_intersections_and_distance():
    """
    Tests spatial intersection and distance calculations for roads and wards.
    """
    road_line = LineString([(85.81, 20.25), (85.85, 20.25)])
    ward_poly = Polygon([
        (85.82, 20.20),
        (85.84, 20.20),
        (85.84, 20.30),
        (85.82, 20.30),
        (85.82, 20.20)
    ])

    # Intersects check
    assert road_line.intersects(ward_poly)

    # Distance calculation between disconnected features
    disjoint_point = Point(85.90, 20.25)
    dist = disjoint_point.distance(ward_poly)
    assert dist > 0.05


def test_gis_boundary_edge_cases():
    """
    Tests boundary conditions: point exactly on boundary, empty geometries, invalid polygons.
    """
    ward_poly = Polygon([
        (85.82, 20.20),
        (85.84, 20.20),
        (85.84, 20.30),
        (85.82, 20.30),
        (85.82, 20.20)
    ])

    # Point on boundary
    boundary_point = Point(85.82, 20.25)
    assert ward_poly.intersects(boundary_point)
    assert not ward_poly.contains(boundary_point)

    # Valid check for self-intersecting polygon fix using buffer(0)
    invalid_bowtie_poly = Polygon([(0, 0), (0, 2), (2, 0), (2, 2), (0, 0)])
    assert not invalid_bowtie_poly.is_valid
    fixed_poly = invalid_bowtie_poly.buffer(0)
    assert fixed_poly.is_valid
