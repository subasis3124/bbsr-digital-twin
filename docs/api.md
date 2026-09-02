# Bhubaneswar Digital Twin — Complete REST API Reference

This document provides complete documentation for the REST API endpoints exposed by the **Bhubaneswar Digital Twin** FastAPI backend (`backend/app`).

---

## 🌐 Overview & Base URL

- **Base URL**: `http://localhost:8000/api/v1`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

All spatial vector endpoints return GeoJSON compliant payloads (`Feature` or `FeatureCollection`). API responses carry standardized `provenance` metadata headers.

---

## 🩺 1. System Health API

### `GET /health`
- **Purpose**: Verifies application, PostgreSQL database connectivity, and PostGIS spatial extension availability.
- **Parameters**: None.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "postgis": "available",
    "postgis_version": "POSTGIS=\"3.3.2\""
  }
  ```
- **Error Response (503 Service Unavailable)**:
  ```json
  {
    "detail": {
      "status": "unhealthy",
      "database": "disconnected",
      "postgis": "unavailable"
    }
  }
  ```

---

## 🗺️ 2. Spatial Infrastructure Vector APIs

### `GET /api/v1/cities`
- **Purpose**: Retrieves city boundary polygon vectors.
- **Response**: GeoJSON `FeatureCollection` (EPSG:4326).

### `GET /api/v1/wards`
- **Purpose**: Retrieves municipal ward boundaries and demographic metadata.
- **Parameters**: `limit` (default 100), `ward_number` (optional).

### `GET /api/v1/roads`
- **Purpose**: Retrieves road network linestrings with speed limit classifications.
- **Parameters**: `limit`, `ward_id`, `road_type`.

### `GET /api/v1/buildings`
- **Purpose**: Retrieves 2D footprint polygons and 3D extrusion heights for urban buildings.
- **Parameters**: `limit`, `bbox`.

### `GET /api/v1/hospitals`
- **Purpose**: Healthcare infrastructure point features, bed capacities, and ward IDs.

### `GET /api/v1/police` & `GET /api/v1/fire-stations`
- **Purpose**: Public safety and emergency response station locations.

### `GET /api/v1/water-bodies`
- **Purpose**: Natural hydrography polygons (lakes, rivers, drainage channels).

### `GET /api/v1/bus-routes` & `GET /api/v1/bus-stops`
- **Purpose**: CRUT urban bus transit network linestrings and stop point locations.

---

## 🌊 3. Flood Risk Modeling API

### `GET /api/v1/flood-risk/grid`
- **Purpose**: Retrieves spatial grid cells with predicted flood probabilities and SHAP feature attributions.
- **Parameters**:
  - `limit`: Integer (1–1000, default 100).
  - `risk_level`: String (`LOW`, `MEDIUM`, `HIGH`, `VERY HIGH`).
  - `ward_id`: Integer (optional).
- **Response Example**:
  ```json
  {
    "type": "FeatureCollection",
    "provenance": {
      "is_synthetic": false,
      "model_name": "RandomForest_FloodRisk_v1"
    },
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Polygon", "coordinates": [...] },
        "properties": {
          "cell_id": 42,
          "risk_level": "HIGH",
          "predicted_probability": 0.78,
          "shap_attribution": { "elevation_m": -0.42, "ndwi": 0.31 }
        }
      }
    ]
  }
  ```

---

## 🚦 4. Traffic & GNN Forecasting APIs

### `GET /api/v1/traffic/predictions`
- **Purpose**: Retrieves baseline spatio-temporal road segment traffic speed predictions.

### `GET /api/v1/gnn/traffic`
- **Purpose**: Retrieves Spatio-Temporal Graph Neural Network (ST-GNN) traffic forecasts over graph topology.
- **Parameters**:
  - `limit`: Integer (default 50).
  - `forecast_horizon_minutes`: Integer (0 to 120, default 0).
  - `road_id`: Integer (optional).

---

## 🌬️ 5. Air Quality Forecasting API

### `GET /api/v1/air-quality`
- **Purpose**: Retrieves pollutant concentrations ($PM_{2.5}$, $PM_{10}$, $NO_2$, $SO_2$, $CO$, $O_3$) and AQI sub-indices.
- **Parameters**: `pollutant`, `horizon_hours`, `station_name`, `bbox`, `limit`.

---

## 🏙️ 6. Unified City State Engine API

### `GET /api/v1/city-state`
- **Purpose**: Retrieves canonical aggregated urban state indicators across spatial units.
- **Parameters**: `limit`, `spatial_unit_type` (`ward` or `grid_cell`).

### `GET /api/v1/city-state/snapshot`
- **Purpose**: Retrieves metadata snapshot of current multi-domain city status.

---

## 🌧️ 7. What-If Simulation Engine API

### `POST /api/v1/simulations`
- **Purpose**: Executes counterfactual simulation (`heavy_rainfall`, `road_closure`, `air_pollution`, `emergency_demand`).
- **Request Body**:
  ```json
  {
    "scenario_type": "heavy_rainfall",
    "parameters": { "rainfall_intensity_mm": 120.0 },
    "spatial_scope": { "ward_ids": [12, 14] }
  }
  ```
- **Response**: Full `SimulationRun` object containing `simulation_id`, `impact_summary`, and `provenance`.

### `GET /api/v1/simulations/{simulation_id}/impact`
- **Purpose**: Retrieves quantitative metric deltas and severity rating for a simulation.

---

## 🚑 8. Emergency Resource Optimization API

### `POST /api/v1/optimization/emergency`
- **Purpose**: Executes OR-Tools capacitated vehicle allocation solver under normal or simulated emergency stress.
- **Request Body**:
  ```json
  {
    "resource_types": ["hospital"],
    "method": "ortools_min_cost_flow",
    "simulation_id": "optional_simulation_uuid"
  }
  ```
- **Response**: Allocations array, total travel cost, baseline heuristic comparison, and served vs unserved demand metrics.

---

## 📊 9. Command Center Dashboard API

### `GET /api/v1/dashboard/summary`
- **Purpose**: Returns high-level city KPI counts for header indicators (AQI average, traffic speed, active flood alert cells).

---

## 🤖 10. Natural Language AI Interface API

### `POST /api/v1/ai/query`
- **Purpose**: Processes natural language query, performs intent classification, executes tool chain, and returns map actions and narrative answer.
- **Request Body**:
  ```json
  {
    "query": "Show high flood-risk areas in Ward 12",
    "provider": "mock"
  }
  ```
- **Response**:
  ```json
  {
    "query": "Show high flood-risk areas in Ward 12",
    "intent": "FLOOD_QUERY",
    "tool_calls": [
      {
        "tool_name": "get_flood_risk",
        "parameters": { "risk_level": "HIGH", "ward_id": 12 },
        "result_count": 8
      }
    ],
    "map_actions": [
      { "action_type": "highlight_cells", "risk_level": "HIGH" }
    ],
    "answer": "Found 8 high flood-risk cells in Ward 12.",
    "provenance": {
      "data_provenance_status": "twin_tool_execution",
      "is_synthetic": false
    }
  }
  ```

### `GET /api/v1/ai/tools`
- **Purpose**: Returns controlled AI tool definitions registered in `TOOL_REGISTRY`.
