import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from shapely.geometry import MultiPolygon, Polygon, Point
from geoalchemy2.shape import from_shape

from pipelines.sources.flood_target import FloodTargetPipeline
from ml.spatial_cv import SpatialBlockSplitter
from ml.feature_extractor import FeatureExtractor
from ml.train import train_pipeline

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def dummy_grid_df():
    data = []
    # Create 20 sample grid cells distributed across coordinates
    for i in range(20):
        # Even cells will have lower elevation (flooded), odd cells higher
        lon = 85.80 + (i % 4) * 0.015
        lat = 20.20 + (i // 4) * 0.015
        data.append({
            "cell_id": i + 1,
            "cell_code": f"BBSR-GRID-{i+1}",
            "lon": lon,
            "lat": lat,
            "elevation": 15.0 if i % 2 == 0 else 45.0,
            "slope": 1.0 if i % 2 == 0 else 4.0,
            "ndvi": 0.3 if i % 2 == 0 else 0.6,
            "ndwi": 0.2 if i % 2 == 0 else -0.2,
            "ndbi": -0.3 if i % 2 == 0 else 0.1,
            "population_count": i * 10,
            "dist_to_water": 30.0 if i % 2 == 0 else 800.0,
            "dist_to_road": 100.0,
            "dist_to_building": 15.0,
            "target": 1 if i % 2 == 0 else 0
        })
    return pd.DataFrame(data)

def test_flood_target_pipeline_validate_missing_file():
    pipeline = FloodTargetPipeline()
    # Missing file path validation must return True gracefully rather than failing
    with patch("os.path.exists", return_value=False):
        assert pipeline.validate(MagicMock(), MagicMock(), filepath="fake.geojson") is True

def test_spatial_cv_block_splitter(dummy_grid_df):
    splitter = SpatialBlockSplitter(block_size_degrees=0.01, n_splits=3)
    splits = list(splitter.split(dummy_grid_df, x_col="lon", y_col="lat", label_col="target"))
    
    assert len(splits) == 3
    for train_idx, val_idx in splits:
        assert len(train_idx) > 0
        assert len(val_idx) > 0
        # Assert no overlapping index leakage
        assert set(train_idx).intersection(set(val_idx)) == set()

@patch("ml.feature_extractor.SessionLocal")
def test_feature_extractor(mock_session_class):
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db
    
    # Mock SQL execution return rows
    mock_rows = [
        (1, "BBSR-GRID-1", 85.8, 20.2, 30.0, 2.0, 0.5, -0.1, -0.2, 100, 50.0, 10.0, 5.0),
        (2, "BBSR-GRID-2", 85.9, 20.3, 40.0, 3.0, 0.6, -0.2, -0.3, 200, 500.0, 20.0, 8.0)
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows
    
    extractor = FeatureExtractor()
    df = extractor.extract_features()
    
    assert len(df) == 2
    assert "elevation" in df.columns
    assert "dist_to_water" in df.columns
    assert df.loc[0, "cell_code"] == "BBSR-GRID-1"
    assert df.loc[1, "population_count"] == 200

@patch("ml.train.SessionLocal")
@patch("ml.train.FeatureExtractor")
@patch("ml.train.mlflow")
def test_train_pipeline_synthetic(mock_mlflow, mock_extractor_class, mock_session_class, dummy_grid_df):
    mock_db = MagicMock()
    mock_session_class.return_value = mock_db
    
    # Mock feature extractor dataframe return
    mock_extractor = MagicMock()
    mock_extractor.extract_features.return_value = dummy_grid_df.drop(columns=["target"])
    mock_extractor_class.return_value = mock_extractor
    
    # Mock targets db query (mock empty to let synthetic mode inject dummy targets)
    mock_db.execute.return_value.fetchall.return_value = [(row["cell_id"], 0) for _, row in dummy_grid_df.iterrows()]
    
    # Run pipeline with allow_synthetic=True
    train_pipeline(allow_synthetic=True)
    
    # Assert MLflow logged experiment parameters
    assert mock_mlflow.start_run.called
