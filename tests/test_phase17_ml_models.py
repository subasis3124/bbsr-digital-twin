import pytest
import torch
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from shapely.geometry import LineString

from ml.spatial_cv import SpatialBlockSplitter
from ml.graph_builder import UrbanGraphBuilder
from ml.gnn_models import GNNTrafficForecaster, GraphSAGEPredictor, GCNPredictor, GATPredictor
from ml.gnn_feature_extractor import SpatiotemporalSplitter
from ml.air_quality_splitter import TemporalAirQualitySplitter


# 1. Flood Model & Spatial CV Splitter Testing
def test_spatial_cv_block_splitter_zero_leakage():
    """
    Verifies that spatial block CV splitters create disjoint spatial training and validation sets
    without overlapping coordinate index leakage.
    """
    df_grid = pd.DataFrame([
        {"cell_id": i + 1, "lon": 85.80 + (i % 4) * 0.015, "lat": 20.20 + (i // 4) * 0.015, "elevation": 15.0 if i % 2 == 0 else 45.0, "target": i % 2}
        for i in range(20)
    ])

    splitter = SpatialBlockSplitter(block_size_degrees=0.01, n_splits=3)
    splits = list(splitter.split(df_grid, x_col="lon", y_col="lat", label_col="target"))

    assert len(splits) == 3
    for train_idx, val_idx in splits:
        assert len(train_idx) > 0
        assert len(val_idx) > 0
        # Assert no overlapping index leakage
        assert set(train_idx).intersection(set(val_idx)) == set()


# 2. Traffic Temporal Leakage Protection & Chronological Splitting
def test_traffic_chronological_temporal_splitting():
    """
    Verifies chronological temporal splitting: training set timestamps strictly precede validation set timestamps.
    """
    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    snapshots = [
        {"timestamp": base_time + timedelta(hours=i), "X": torch.randn(3, 10), "y": torch.randn(3, 1)}
        for i in range(10)
    ]

    train_s, val_s, test_s = SpatiotemporalSplitter.split(snapshots, train_ratio=0.6, val_ratio=0.2)

    assert len(train_s) == 6
    assert len(val_s) == 2
    assert len(test_s) == 2

    # Strict chronological ordering check
    assert train_s[-1]["timestamp"] < val_s[0]["timestamp"]
    assert val_s[-1]["timestamp"] < test_s[0]["timestamp"]


# 3. GNN Traffic Graph Determinism & Model Architectures
def test_gnn_graph_structure_determinism():
    """
    Verifies that UrbanGraphBuilder constructs an identical graph structure (adjacency matrix & node mapping)
    given identical inputs and configuration.
    """
    road1 = {"road_id": 1, "osm_id": 101, "name": "Janpath", "highway_type": "primary", "lanes": 4, "maxspeed": 50, "oneway": False, "geom": LineString([(85.82, 20.29), (85.83, 20.30)])}
    road2 = {"road_id": 2, "osm_id": 102, "name": "Rajpath", "highway_type": "secondary", "lanes": 2, "maxspeed": 40, "oneway": False, "geom": LineString([(85.83, 20.30), (85.84, 20.31)])}
    road3 = {"road_id": 3, "osm_id": 103, "name": "Isolated Lane", "highway_type": "residential", "lanes": 1, "maxspeed": 30, "oneway": False, "geom": LineString([(85.90, 20.40), (85.91, 20.41)])}

    roads = [road1, road2, road3]
    builder = UrbanGraphBuilder(db=None)

    res1 = builder.build_graph(roads, add_self_loops=True)
    res2 = builder.build_graph(roads, add_self_loops=True)

    assert res1["num_nodes"] == 3
    assert res1["road_to_idx"][1] == 0
    assert torch.equal(res1["edge_index"], res2["edge_index"])
    assert torch.equal(res1["x_static"], res2["x_static"])


def test_gnn_model_forward_passes():
    """
    Tests forward pass shapes and outputs for GraphSAGE, GCN, and GAT models.
    """
    num_nodes = 4
    in_channels = 14
    hidden_dim = 16

    x = torch.randn(num_nodes, in_channels)
    edge_index = torch.tensor([[0, 1, 2, 3, 0, 1, 2, 3], [1, 0, 3, 2, 0, 1, 2, 3]], dtype=torch.long)

    for arch in ["GraphSAGE", "GCN", "GAT"]:
        model = GNNTrafficForecaster(architecture=arch, in_channels=in_channels, hidden_channels=hidden_dim)
        out = model(x, edge_index)
        assert out.shape == (num_nodes, 1)
        assert not torch.isnan(out).any()
