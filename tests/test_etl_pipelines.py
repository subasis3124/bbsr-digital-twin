import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from shapely.geometry import Polygon, Point
from geoalchemy2.shape import from_shape

from pipelines.etl.provenance import JobContext
from pipelines.sources.copernicus_dem import CopernicusDEMPipeline
from pipelines.sources.worldpop import WorldPopPipeline
from pipelines.sources.sentinel2 import Sentinel2Pipeline
from pipelines.sources.open_meteo import OpenMeteoPipeline
from pipelines.sources.air_quality import AirQualityPipeline

# Mock db and cells data for testing
@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.fixture
def mock_cells():
    cells = []
    # Create two mock cells
    for i in range(1, 3):
        cell = MagicMock()
        cell.id = i
        cell.cell_code = f"BBSR-GRID-{i}"
        cell.geom = from_shape(Polygon([(85.8, 20.2), (85.8, 20.3), (85.9, 20.3), (85.8, 20.2)]), srid=4326)
        cell.centroid = from_shape(Point(85.85, 20.25), srid=4326)
        cells.append(cell)
    return cells

def test_dem_pipeline_validation(mock_db):
    pipeline = CopernicusDEMPipeline()
    context = JobContext("dem", "copernicus-glo30")
    
    with patch("os.path.exists", return_value=False):
        assert pipeline.validate(context, mock_db) is False

def test_sentinel2_pipeline_transform(mock_db, mock_cells):
    pipeline = Sentinel2Pipeline()
    context = JobContext("sentinel2", "sentinel2-ndvi")
    
    mock_db.query.return_value.all.side_effect = [
        mock_cells, # spatial grid cells
        [], # water bodies
        [], # roads
        []  # buildings
    ]
    
    results = pipeline.transform(context, mock_db)
    
    assert len(results) == len(mock_cells)
    # Check that indices were computed
    assert "ndvi" in results[0]
    assert "ndwi" in results[0]
    assert "ndbi" in results[0]
    assert results[0]["ndvi"] > 0.4 # default vegetation value

def test_open_meteo_pipeline_transform(mock_db):
    pipeline = OpenMeteoPipeline()
    context = JobContext("weather", "open-meteo")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2026-08-23T00:00", "2026-08-23T01:00"],
            "temperature_2m": [30.1, 29.5],
            "relative_humidity_2m": [80, 85],
            "precipitation": [0.0, 1.2],
            "wind_speed_10m": [12.5, 10.2]
        }
    }
    
    with patch("requests.get", return_value=mock_response):
        results = pipeline.transform(context, mock_db, backfill_days=1)
        
    assert len(results) == 2
    assert results[0]["temperature"] == 30.1
    assert results[1]["rainfall"] == 1.2
    assert results[0]["source"] == "open-meteo"

def test_air_quality_pipeline_cpcb_calculation():
    pipeline = AirQualityPipeline()
    
    # Test sub-index formula
    assert pipeline._calculate_aqi_pm25(10.0) == 42 # Range 0-12
    assert pipeline._calculate_aqi_pm25(25.0) == 78 # Range 12.1-35.4
    assert pipeline._calculate_aqi_pm25(50.0) == 137 # Range 35.5-55.4
    assert pipeline._calculate_aqi_pm25(100.0) == 174 # Range 55.5-150.4
    assert pipeline._calculate_aqi_pm25(None) is None

def test_air_quality_pipeline_transform_open_meteo(mock_db):
    pipeline = AirQualityPipeline()
    context = JobContext("air_quality", "openaq-cpcb")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2026-08-23T00:00"],
            "pm2_5": [24.0],
            "pm10": [48.0],
            "carbon_monoxide": [280],
            "nitrogen_dioxide": [15],
            "sulphur_dioxide": [8],
            "ozone": [62]
        }
    }
    
    with patch("requests.get", return_value=mock_response):
        results = pipeline._transform_open_meteo_aq(context)
        
    assert len(results) == 1
    assert results[0]["pm25"] == 24.0
    assert results[0]["aqi_value"] == 76
    assert results[0]["source"] == "open-meteo-aq"

def test_worldpop_pipeline_dasymetric_transform(mock_db, mock_cells):
    pipeline = WorldPopPipeline()
    context = JobContext("population", "worldpop-2020")
    
    # Mock Wards
    mock_ward = MagicMock()
    mock_ward.id = 101
    mock_ward.population_est = 1000
    mock_ward.geom = from_shape(Polygon([(85.0, 20.0), (85.0, 21.0), (86.0, 21.0), (86.0, 20.0), (85.0, 20.0)]), srid=4326)
    
    mock_db.query.return_value.all.side_effect = [
        [mock_ward], # db.query(Ward).all()
        mock_cells   # db.query(SpatialGridCell).all()
    ]
    
    results = pipeline._transform_from_wards(context, mock_db)
    
    assert len(results) == 2
    # 1000 population divided over 2 mock cells = 500 per cell
    assert results[0]["population_count"] == 500
