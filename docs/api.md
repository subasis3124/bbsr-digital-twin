# BBSR Digital Twin — API Documentation

This document describes the REST API endpoints exposed by the FastAPI backend (`backend/app`).

---

## 🌐 Overview & Base URL

- **Base URL**: `http://localhost:8000/api/v1`
- **Specification / Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)

All spatial vector endpoints return standard GeoJSON payloads (`Feature` or `FeatureCollection`).

---

## 🌬️ Air Quality Forecasting API (`/api/v1/air-quality`)

### 1. Get Air Quality Forecasts
- **HTTP Method**: `GET /api/v1/air-quality`
- **Summary**: Retrieves predicted air quality pollutant concentrations (PM2.5, PM10, etc.) across stations and forecast horizons. Supports spatial bounding box filtering.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `pollutant` | `string` | No | `"PM2.5"` | Target pollutant (`PM2.5`, `PM10`, `CO`, `NO2`, `SO2`, `O3`) |
| `horizon_hours` | `integer` | No | `None` | Specific forecast horizon in hours (e.g. `1`, `3`, `6`, `12`, `24`) |
| `station_name` | `string` | No | `None` | Filter predictions by station name (e.g. `"Patrapada"`) |
| `bbox` | `string` | No | `None` | Spatial bounding box filter in WGS84: `"min_lon,min_lat,max_lon,max_lat"` |
| `limit` | `integer` | No | `100` | Maximum number of features returned (1 to 1000) |
| `offset` | `integer` | No | `0` | Offset for pagination |

#### Response Format (GeoJSON FeatureCollection):
```json
{
  "type": "FeatureCollection",
  "provenance": {
    "data_provenance_status": "synthetic_fallback",
    "scientific_validation_warning": "Warning: Predictions generated using synthetic training data."
  },
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [85.824, 20.296]
      },
      "properties": {
        "id": 1,
        "station_name": "Patrapada",
        "pollutant": "PM2.5",
        "forecast_issue_time": "2026-08-24T12:00:00Z",
        "target_time": "2026-08-24T18:00:00Z",
        "horizon_hours": 6,
        "predicted_value": 35.5,
        "aqi_sub_index": 101,
        "model_name": "xgboost_regressor",
        "model_version": "1.0.0",
        "is_synthetic": true
      }
    }
  ]
}
```

---

## 🚦 Traffic Forecasting API (`/api/v1/traffic`)

### 1. Get Traffic Predictions
- **HTTP Method**: `GET /api/v1/traffic/predictions`
- **Summary**: Retrieves predicted traffic speed and congestion ratio across road segments.

---

## 🌊 Flood Risk API (`/api/v1/flood-risk`)

### 1. Get Flood Risk Grid Cells
- **HTTP Method**: `GET /api/v1/flood-risk/grid`
- **Summary**: Retrieves spatial grid cells with associated flood risk probabilities.

---

## 🧪 Health & System Status

### 1. Health Check
- **HTTP Method**: `GET /health`
- **Summary**: Returns operational status of database connection and spatial capabilities.
