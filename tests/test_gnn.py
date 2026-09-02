import pytest
import torch
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from shapely.geometry import LineString
from geoalchemy2.shape import from_shape

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Road, GNNTrafficPrediction
from ml.graph_builder import UrbanGraphBuilder
from ml.gnn_feature_extractor import GNNFeatureExtractor, SpatiotemporalSplitter
from ml.gnn_models import GNNTrafficForecaster, GraphSAGEPredictor, GCNPredictor, GATPredictor
from ml.gnn_train import train_and_evaluate_gnn, set_seed

client = TestClient(app)

# 1. Test Graph Construction & Determinism
def test_graph_builder_determinism():
    road1 = {
        "road_id": 1,
        "osm_id": 101,
        "name": "Janpath",
        "highway_type": "primary",
        "lanes": 4,
        "maxspeed": 50,
        "oneway": False,
        "geom": LineString([(85.82, 20.29), (85.83, 20.30)])
    }
    road2 = {
        "road_id": 2,
        "osm_id": 102,
        "name": "Rajpath",
        "highway_type": "secondary",
        "lanes": 2,
        "maxspeed": 40,
        "oneway": False,
        "geom": LineString([(85.83, 20.30), (85.84, 20.31)])  # Connects to road1 at (85.83, 20.30)
    }
    road3 = {
        "road_id": 3,
        "osm_id": 103,
        "name": "Isolated Lane",
        "highway_type": "residential",
        "lanes": 1,
        "maxspeed": 30,
        "oneway": False,
        "geom": LineString([(85.90, 20.40), (85.91, 20.41)])  # Isolated
    }

    roads = [road1, road2, road3]
    builder = UrbanGraphBuilder(db=None)

    res1 = builder.build_graph(roads, add_self_loops=True)
    res2 = builder.build_graph(roads, add_self_loops=True)

    assert res1["num_nodes"] == 3
    assert res1["road_to_idx"][1] == 0
    assert res1["road_to_idx"][2] == 1
    assert res1["road_to_idx"][3] == 2
    assert res1["idx_to_road"][0] == 1

    # Determinism check
    assert torch.equal(res1["edge_index"], res2["edge_index"])
    assert torch.equal(res1["x_static"], res2["x_static"])

    # Disconnected component & isolated node stats check
    stats = res1["statistics"]
    assert stats["num_nodes"] == 3
    assert stats["num_connected_components"] >= 2
    assert stats["num_isolated_nodes"] == 1


# 2. Test Spatiotemporal Feature Extractor & Splitter (Zero Leakage)
def test_spatiotemporal_splitter():
    snaps = []
    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    for i in range(10):
        snaps.append({
            "timestamp": base_time + timedelta(hours=i),
            "X": torch.randn(3, 14),
            "y": torch.randn(3, 1),
            "mask": torch.tensor([True, True, True]),
            "df_snapshot": None
        })

    train_s, val_s, test_s = SpatiotemporalSplitter.split(snaps, train_ratio=0.6, val_ratio=0.2)

    assert len(train_s) == 6
    assert len(val_s) == 2
    assert len(test_s) == 2

    # Chronological strict ordering
    assert train_s[-1]["timestamp"] < val_s[0]["timestamp"]
    assert val_s[-1]["timestamp"] < test_s[0]["timestamp"]


# 3. Test GNN PyTorch Models Forward Pass & Tensor Shapes
def test_gnn_model_architectures():
    set_seed(42)
    num_nodes = 5
    in_channels = 14
    hidden_dim = 32
    
    x = torch.randn(num_nodes, in_channels)
    # Simple star graph topology edge index with self loops
    edge_index = torch.tensor([
        [0, 1, 2, 3, 4, 0, 1, 2, 3, 4],
        [1, 0, 0, 0, 0, 0, 1, 2, 3, 4]
    ], dtype=torch.long)

    # GraphSAGE
    model_sage = GNNTrafficForecaster(architecture="GraphSAGE", in_channels=in_channels, hidden_channels=hidden_dim)
    out_sage = model_sage(x, edge_index)
    assert out_sage.shape == (num_nodes, 1)
    assert not torch.isnan(out_sage).any()

    # GCN
    model_gcn = GNNTrafficForecaster(architecture="GCN", in_channels=in_channels, hidden_channels=hidden_dim)
    out_gcn = model_gcn(x, edge_index)
    assert out_gcn.shape == (num_nodes, 1)
    assert not torch.isnan(out_gcn).any()

    # GAT
    model_gat = GNNTrafficForecaster(architecture="GAT", in_channels=in_channels, hidden_channels=hidden_dim)
    out_gat = model_gat(x, edge_index)
    assert out_gat.shape == (num_nodes, 1)
    assert not torch.isnan(out_gat).any()


# 4. Test Tiny Graph Training Smoke Test & Convergence
def test_tiny_gnn_training_loop():
    set_seed(42)
    num_nodes = 4
    in_channels = 10
    
    x = torch.randn(num_nodes, in_channels)
    y = torch.tensor([[30.0], [45.0], [50.0], [25.0]], dtype=torch.float32)
    edge_index = torch.tensor([
        [0, 1, 1, 2, 2, 3, 0, 1, 2, 3],
        [1, 0, 2, 1, 3, 2, 0, 1, 2, 3]
    ], dtype=torch.long)

    model = GNNTrafficForecaster(architecture="GraphSAGE", in_channels=in_channels, hidden_channels=16, num_layers=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = torch.nn.MSELoss()

    initial_loss = criterion(model(x, edge_index), y).item()

    for _ in range(30):
        optimizer.zero_grad()
        pred = model(x, edge_index)
        loss = criterion(pred, y)
        loss.backward()
        optimizer.step()

    final_loss = criterion(model(x, edge_index), y).item()
    assert final_loss < initial_loss


# 5. Test API Endpoints: Empty & Rich Mock Sessions
def test_gnn_api_empty():
    class EmptyMockQuery:
        def join(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def offset(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def all(self):
            return []
        def first(self):
            return None

    class EmptyMockSession:
        def query(self, model):
            return EmptyMockQuery()
        def close(self):
            pass

    def override_db_empty():
        yield EmptyMockSession()

    app.dependency_overrides[get_db] = override_db_empty
    try:
        response = client.get("/api/v1/gnn/traffic")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 0

        # Test graph stats endpoint with empty DB
        response_stats = client.get("/api/v1/gnn/traffic/graph")
        assert response_stats.status_code == 200
        stats_json = response_stats.json()
        assert "graph_statistics" in stats_json
    finally:
        app.dependency_overrides[get_db] = get_db


def test_gnn_api_rich():
    line = LineString([(85.82, 20.29), (85.83, 20.30)])
    mock_road = Road(
        id=1,
        osm_id=101,
        name="Janpath Road",
        highway_type="primary",
        lanes=4,
        maxspeed=50,
        geom=from_shape(line, srid=4326)
    )

    mock_pred = GNNTrafficPrediction(
        id=1,
        road_id=1,
        prediction_time=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        forecast_horizon_minutes=60,
        predicted_speed=41.5,
        predicted_congestion_ratio=0.17,
        gnn_architecture="GraphSAGE",
        model_name="GNN_GraphSAGE",
        model_version="1.0.0",
        is_synthetic=True,
        data_provenance_status="synthetic_fallback",
        road=mock_road
    )

    class RichMockQuery:
        def join(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def offset(self, val):
            return self
        def limit(self, val):
            return self
        def all(self):
            return [mock_pred]
        def first(self):
            return mock_pred

    class RichMockSession:
        def query(self, model):
            return RichMockQuery()
        def close(self):
            pass

    def override_db_rich():
        yield RichMockSession()

    app.dependency_overrides[get_db] = override_db_rich
    try:
        # Bounding box spatial test
        res = client.get("/api/v1/gnn/traffic?min_lon=85.0&min_lat=20.0&max_lon=86.0&max_lat=21.0")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["properties"]["road_id"] == 1
        assert feat["properties"]["predicted_speed"] == 41.5
        assert feat["properties"]["gnn_architecture"] == "GraphSAGE"
        assert feat["properties"]["is_synthetic"] is True
        assert "scientific_validation_warning" in feat["properties"]

        # Road detail lookup test
        res_road = client.get("/api/v1/gnn/traffic/1")
        assert res_road.status_code == 200
        road_data = res_road.json()
        assert road_data["type"] == "Feature"
        assert road_data["properties"]["road_id"] == 1
        assert road_data["properties"]["predicted_speed"] == 41.5
    finally:
        app.dependency_overrides[get_db] = get_db
