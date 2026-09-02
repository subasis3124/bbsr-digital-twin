# Phase 10 — Graph Neural Network (GNN) Urban Forecasting Architecture

## 1. Overview
Phase 10 implements an academically credible, reproducible, and scalable Graph Neural Network (GNN) urban intelligence layer for the Bhubaneswar Digital Twin repository. The GNN models spatial road network topology combined with chronological temporal traffic observations to perform spatial-temporal road speed and congestion forecasting.

The GNN architecture serves as a foundation for downstream Digital Twin engines:
- **Phase 11**: Unified City State Engine
- **Phase 12**: What-if Simulation Engine
- **Phase 13**: Emergency Resource Optimization

---

## 2. Graph Topology & Semantics

### Nodes ($V$)
- **Node Entity**: PostGIS Road segments (`Road` model, `roads` table).
- **Node Identifier**: Contiguous integer indices $0 \dots N-1$ mapped deterministically to database primary keys (`road_id`).
- **Node Attributes**:
  - Static spatial properties: Estimated segment length, speed limit (`maxspeed`), lane count, highway classification (one-hot encoded), spatial centroid coordinates (normalized longitude & latitude), node degree.
  - Dynamic temporal properties: Chronological speed lags (`lag_1h`, `lag_2h`, `lag_24h`), 3-hour rolling average speed, hour of day, day of week, weekend indicator, holiday indicator.

### Edges ($E$)
- **Edge Definition**: Physical spatial/topological adjacency between road segments (LineStrings intersecting, touching, or within a spatial threshold buffer of ~50m).
- **Directionality**: Directed edges corresponding to `oneway` attribute, with bidirectional edges added for two-way roads. Self-loops are included to ensure stable message passing across isolated node components.
- **Edge Weights**: Distance-weighted connectivity $w_{u,v} = \max(1.0, \frac{1}{1.0 + 1000 \cdot d(u,v)})$.

---

## 3. Leakage-Safe Temporal Methodology

To prevent future lookahead leakage in spatiotemporal forecasting:
1. **Target Pre-shifting**: Observation targets are shifted by 1 timestep before generating lag variables and rolling statistics. At time $t$, features only contain information available at or before time $t$.
2. **Chronological Partitioning**:
   - **Train**: Earliest 60% of time snapshots.
   - **Validation**: Subsequent 20% of time snapshots.
   - **Test**: Latest unseen 20% of time snapshots.
   *Random splitting is strictly prohibited for temporal graph forecasting.*

---

## 4. GNN Models & Baselines

### GNN Architectures (`ml/gnn_models.py`)
- **GraphSAGE (`GraphSAGEPredictor`)**: Neighborhood mean aggregation over spatial road topology.
- **GCN (`GCNPredictor`)**: Spectral graph convolution with degree normalization.
- **GAT (`GATPredictor`)**: Multi-head graph attention over topological road neighbors.

### Baselines (`ml/traffic_models.py`, `ml/gnn_train.py`)
- **Naive Baseline**: Last observed speed at $t-1$.
- **Historical Average**: Mean road speed per segment.
- **XGBoost Regressor**: Standard gradient-boosted decision trees operating on flat tabular features.

---

## 5. Pipeline Execution & MLflow Integration

### Training Command
```bash
python ml/gnn_train.py --architecture GraphSAGE --hidden-dim 64 --num-layers 2 --epochs 40 --allow-synthetic
```

### MLflow Logging
Experiment metrics are recorded under tracking database `sqlite:////tmp/mlflow_bbsr.db`:
- Model hyperparameters (architecture, hidden channels, num layers, learning rate, random seed).
- Graph topology statistics (nodes, edges, connected components, isolated nodes, average degree).
- Test set metrics (MAE, RMSE, R²).
- Baseline performance comparisons.
- Model checkpoint artifact (`models/gnn_traffic_model.pt`).

---

## 6. Database Persistence & API Integration

### Database Model & Alembic Migration
- **Table**: `gnn_traffic_predictions`
- **Migration Revision**: `d10a10a10a10`
- **Fields**: `id`, `road_id`, `prediction_time`, `forecast_horizon_minutes`, `predicted_speed`, `predicted_congestion_ratio`, `gnn_architecture`, `model_name`, `model_version`, `created_at`, `is_synthetic`, `data_provenance_status`.

### API Endpoints (`backend/app/routes/gnn_traffic.py`)
- `GET /api/v1/gnn/traffic`: GeoJSON FeatureCollection of GNN road predictions with bounding-box spatial filter (`min_lon`, `min_lat`, `max_lon`, `max_lat`), `road_id`, `prediction_time`, and pagination.
- `GET /api/v1/gnn/traffic/graph`: Graph topology statistics and provenance metadata.
- `GET /api/v1/gnn/traffic/{road_id}`: GeoJSON Feature for single road segment forecast.

---

## 7. Scientific Integrity & Provenance

In accordance with project integrity standards:
- If synthetic observation fallback data is present during training, the model marks stored predictions with `is_synthetic = True` and `data_provenance_status = "synthetic_fallback"`.
- Public API responses attach explicit `scientific_validation_warning` flags when serving synthetic fallback predictions.
