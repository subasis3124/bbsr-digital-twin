# Bhubaneswar Digital Twin — Data Provenance & Lineage Specification

This document details data sources, ingestion pipelines, transformations, storage layers, model usage, synthetic data status, and scientific limitations for all data families within the **Bhubaneswar Digital Twin**.

---

## 📊 Data Family Provenance Summary Matrix

| Data Family | Source | Ingestion Pipeline | Storage Table / Format | Synthetic Status | Primary Model / System Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OSM / Vector GIS** | OpenStreetMap, BMC GIS | `pipelines/sources/vector.py` | `roads`, `wards`, `cities` | Real Spatial Vectors | Basemap, Spatial Join, GNN Graph Topology |
| **Elevation (DEM)** | SRTM 30m / USGS | `pipelines/etl/flood_etl.py` | GeoTIFF / `spatial_grid_cells` | Real Topography | Flood Risk Model (Elevation, Slope) |
| **Population** | Census India / BMC | `pipelines/sources/wards.py` | `wards.population` | Administrative Census | Spatial Aggregation, Demand Weighting |
| **Sentinel Remote Sensing** | Sentinel-2 L2A | `ml/feature_extractor.py` | `spatial_grid_cells.ndwi` | Real Remote Sensing | NDWI Water Index, Flood Classification |
| **Weather & Rainfall** | OpenMeteo API | `pipelines/sources/weather.py` | `openmeteo_observations` | Real Meteorological | Flood & Air Quality Forecast Inputs |
| **Traffic Speed & Flow** | Sensor Feed / Synthetic | `pipelines/sources/traffic.py` | `traffic_observations` | Synthetic Fallback | Traffic Speed & GNN Spatio-Temporal Models |
| **Air Quality (AQI)** | CPCB / OpenAQ | `pipelines/sources/air_quality.py`| `air_quality_observations` | Synthetic Fallback | XGBoost Air Quality Forecaster |
| **Urban Infrastructure** | BMC / CRUT GIS | `pipelines/sources/infrastructure.py` | `hospitals`, `schools`, `police`, `fire_stations` | Real Infrastructure | Resource Allocation & Emergency Optimization |
| **Synthetic Integration** | Generator Scripts | `tests/fixtures/` | InMemory / SQLite Mock | Fully Synthetic | E2E Integration & Stress Testing |

---

## 🔍 Detailed Data Family Lineage

### 1. Vector Infrastructure (OSM & BMC GIS)
- **Source**: OpenStreetMap (OSM) spatial extracts and Bhubaneswar Municipal Corporation (BMC) spatial layers.
- **Ingestion**: `pipelines/sources/vector.py` parses GeoJSON and Shapefiles.
- **Transformation**: Reprojected from native CRS to WGS84 (`EPSG:4326`). Spatial boundaries clipped to Bhubaneswar bounding box `[85.70, 20.15, 85.95, 20.45]`.
- **Storage**: PostGIS tables `cities`, `wards`, `roads`, `buildings`, `water_bodies`, `bus_routes`, `bus_stops`.
- **Synthetic Status**: **Real spatial vector geometries**.
- **Limitations**: Vector features reflect snap-shot OpenStreetMap state and may not reflect unmapped local minor roads.

---

### 2. Digital Elevation Model (DEM) & Slope
- **Source**: SRTM 30-meter Shuttle Radar Topography Mission elevation raster tiles.
- **Ingestion**: `pipelines/etl/flood_etl.py` clips raster extent and computes slope derivatives.
- **Transformation**: Extracted raster statistics sampled at 500m × 500m spatial grid cell centroids.
- **Storage**: Attributes `elevation_m` and `slope_deg` on `spatial_grid_cells` PostGIS table.
- **Synthetic Status**: **Real topographic DEM measurements**.
- **Limitations**: 30m resolution smooths micro-topography (e.g. roadside curbs, small drainage channels).

---

### 3. Sentinel-2 Remote Sensing Imagery Indices
- **Source**: Copernicus Sentinel-2 MultiSpectral Instrument (MSI) surface reflectance bands (B03 Green, B08 NIR).
- **Transformation**: Computation of Normalized Difference Water Index (NDWI):
  $$\text{NDWI} = \frac{\text{Band 3} - \text{Band 8}}{\text{Band 3} + \text{Band 8}}$$
- **Storage**: `spatial_grid_cells.ndwi` column.
- **Synthetic Status**: **Derived real satellite imagery index**.
- **Limitations**: Cloud cover during monsoon season limits cloud-free optical acquisition frequency.

---

### 4. Weather & Rainfall Observations
- **Source**: OpenMeteo Historical & Forecast API for Bhubaneswar coordinates (`20.296°N, 85.824°E`).
- **Ingestion**: `pipelines/sources/weather.py` fetches hourly precipitation, temperature, relative humidity, and wind speed.
- **Transformation**: Aggregated to 1-hour, 3-hour, and 24-hour cumulative rainfall totals.
- **Storage**: `openmeteo_observations` table in PostgreSQL.
- **Synthetic Status**: **Real weather API observation & forecast data** (with synthetic fallback if API unreachable).

---

### 5. Traffic Observations & GNN Networks
- **Source**: Simulated vehicle loop detectors calibrated to urban arterial road capacities.
- **Transformation**: Speed (km/h), volume (veh/hr), and congestion ratio ($\text{speed} / \text{speed\_limit}$) per road segment.
- **Storage**: `traffic_observations`, `traffic_predictions`, `gnn_traffic_predictions`.
- **Synthetic Status**: **Synthetic fallback data**. Real telemetry API integrated when available.
- **Limitations**: Synthetic traffic profiles model typical diurnal commuting patterns (morning/evening peaks) but lack real-time Bluetooth/GPS probe telemetry.

---

### 6. Air Quality Sensor Observations
- **Source**: Central Pollution Control Board (CPCB) continuous ambient air monitoring stations (Patrapada, Kalinga Nagar, Chandrasekharpur).
- **Transformation**: Micrograms per cubic meter ($\mu g/m^3$) per pollutant (PM2.5, PM10, NO2, SO2, CO, O3) and computed Indian AQI sub-indices.
- **Storage**: `air_quality_observations`, `air_quality_predictions`.
- **Synthetic Status**: **Synthetic fallback data**.
- **Limitations**: Air quality sensors have sparse spatial coverage across the 67 municipal wards; spatial interpolation is used for unsampled areas.

---

### 7. Synthetic Integration Datasets
- **Purpose**: Used exclusively for automated CI/CD unit tests, regression tests, and simulation stress testing.
- **Synthetic Status**: **Fully Synthetic**.
- **Safeguard**: Every record generated carries explicit JSON metadata:
  ```json
  "provenance": {
    "is_synthetic": true,
    "scientific_validation_warning": "Warning: Predictions generated using synthetic training data."
  }
  ```
