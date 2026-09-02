# Bhubaneswar Digital Twin — ML Model Cards

This document provides standardized **Model Cards** for the machine learning and deep learning models deployed within the **Bhubaneswar Digital Twin** system.

---

## 🛈 Scientific Disclaimer

> [!CAUTION]
> **Scientific Integrity & Validation Notice**: The metrics reported below are obtained from **synthetic integration experiments** and cross-validation pipelines designed to verify software pipeline correctness, non-leaking temporal splits, and graph convergence. They represent **software validation**, not real-world empirical validation against physical ground truth. Model outputs serve decision support and counterfactual simulation purposes only.

---

## 🃏 Model Card 1: Flood Risk Classifier

### Overview
- **Model Name**: `RandomForest_FloodRisk_v1`
- **Purpose**: Predicts spatial flood risk probability across 500m × 500m urban grid cells under heavy rainfall events.
- **Model Type**: Random Forest Classifier / Gradient Boosting.

### Inputs & Features
- `elevation_m`: Grid cell mean terrain elevation from DEM (meters above sea level).
- `slope_deg`: Topographic slope gradient (degrees).
- `ndwi`: Sentinel-2 Normalized Difference Water Index.
- `distance_to_river_m`: Euclidean distance to nearest natural river or major drainage channel (meters).
- `rainfall_24h_mm`: Cumulative 24-hour precipitation (mm).

### Outputs
- `risk_level`: Multi-class flood risk label (`LOW`, `MEDIUM`, `HIGH`, `VERY HIGH`).
- `predicted_probability`: Calibrated flood probability ($[0.0, 1.0]$).
- `shap_attribution`: Feature importance attribution values.

### Training Methodology & Spatial Cross-Validation
- **Validation Strategy**: Spatial Block Cross-Validation (`SpatialBlockCV`) using non-overlapping 2km × 2km spatial block clusters to prevent spatial autocorrelation leakage.
- **Evaluation Status**: **Synthetic integration experiment**.

### Performance Metrics (Synthetic Integration Benchmark)
- **Accuracy**: $0.88$ (Synthetic benchmark)
- **F1 Score (High Risk)**: $0.85$ (Synthetic benchmark)
- **ROC-AUC**: $0.92$ (Synthetic benchmark)

### Data Provenance & Synthetic Status
- **Terrain/DEM**: Real SRTM DEM data.
- **Water Index**: Real Sentinel-2 NDWI imagery.
- **Labels**: Synthetic historical flood extent labels.

### Limitations
- Does not model dynamic 2D hydrodynamic wave propagation or pipe-network urban drainage capacities.

---

## 🃏 Model Card 2: Traffic Speed Forecaster

### Overview
- **Model Name**: `RidgeXGBoost_TrafficSpeed_v1`
- **Purpose**: Predicts multi-step traffic speed (km/h) and congestion ratio per road segment across short forecast horizons (15, 30, 60 minutes).

### Inputs & Features
- `historical_speed_t-15`, `historical_speed_t-30`: Prior road segment speeds.
- `road_type`: Categorical classification (`motorway`, `primary`, `secondary`, `residential`).
- `speed_limit`: Legal speed limit (km/h).
- `hour_of_day`, `day_of_week`: Temporal cyclic features ($\sin/\cos$ transformations).
- `rainfall_1h_mm`: Concurrent rainfall intensity.

### Outputs
- `predicted_speed`: Predicted vehicular speed (km/h).
- `congestion_ratio`: Congestion ratio ($\text{predicted\_speed} / \text{speed\_limit}$).

### Training Methodology & Chronological Splitter
- **Validation Strategy**: Strict Chronological Temporal Split ($T_{\text{train}} < T_{\text{val}} < T_{\text{test}}$) to ensure zero future-data temporal leakage.

### Performance Metrics (Synthetic Integration Benchmark)
- **MAE**: $3.2\text{ km/h}$ (Synthetic benchmark)
- **RMSE**: $4.8\text{ km/h}$ (Synthetic benchmark)
- **$R^2$ Score**: $0.81$ (Synthetic benchmark)

### Data Provenance & Synthetic Status
- **Road Network**: Real OpenStreetMap road vector geometry.
- **Observations**: Synthetic traffic loop detector speed profiles.

### Limitations
- Assumes normal traffic dynamics; does not predict sudden unplanned road accidents without explicit scenario inputs.

---

## 🃏 Model Card 3: Air Quality Forecaster

### Overview
- **Model Name**: `XGBoost_AirQuality_v1`
- **Purpose**: Forecasts ambient air quality pollutant concentrations ($PM_{2.5}$, $PM_{10}$, $NO_2$) across 1 to 24-hour forecast horizons.

### Inputs & Features
- `pm25_lag1`, `pm25_lag3`, `pm25_lag24`: Lagged pollutant observations.
- `temperature_c`, `humidity_pct`, `wind_speed_ms`: Meteorological parameters.
- `station_id`: AQI monitoring station identifier.

### Outputs
- `predicted_value`: Forecasted concentration ($\mu g/m^3$).
- `aqi_category`: Indian National Air Quality Index category (`Good`, `Satisfactory`, `Moderate`, `Poor`, `Very Poor`, `Severe`).

### Training Methodology & Temporal Split
- **Validation Strategy**: Chronological Time-Series Split.

### Performance Metrics (Synthetic Integration Benchmark)
- **MAE ($PM_{2.5}$)**: $4.1\text{ }\mu g/m^3$ (Synthetic benchmark)
- **RMSE**: $6.3\text{ }\mu g/m^3$ (Synthetic benchmark)

### Data Provenance & Synthetic Status
- **Station Locations**: Real CPCB station coordinates.
- **Observations**: Synthetic fallback time-series.

---

## 🃏 Model Card 4: Graph Neural Network (GNN) Traffic Forecaster

### Overview
- **Model Name**: `SpatioTemporal_STGNN_v1`
- **Purpose**: Forecasts network-wide traffic flow and speed propagation across the road graph topology using spatial message passing and temporal convolutions.
- **Architecture**: GraphSAGE / GCN backbone with temporal GRU layers.

### Graph Topography & Inputs
- **Nodes**: Road intersections / segment midpoints ($N = \text{Road segments}$).
- **Edges**: Physical road adjacency network connections derived from PostGIS linestrings.
- **Node Attributes**: Historical speed vector, segment capacity, road type embedding.

### Outputs
- Node-level forecasted traffic speed ($V_{i, t+h}$) and flow volume.

### Training Methodology & Determinism Verification
- **Loss Function**: Mean Squared Error (MSE) loss over connected graph nodes.
- **Determinism**: PyTorch seed pinning (`torch.manual_seed(42)`) verified for 100% reproducible forward passes.

### Performance Metrics (Synthetic Integration Benchmark)
- **Graph MAE**: $2.9\text{ km/h}$ (Synthetic benchmark)
- **Graph RMSE**: $4.1\text{ km/h}$ (Synthetic benchmark)

### Data Provenance & Synthetic Status
- **Graph Topology**: Real OpenStreetMap road graph network topology.
- **Node Signals**: Synthetic traffic loop observations.

### Limitations
- Static graph topology; dynamic road construction closures require graph adjacency matrix updates.
