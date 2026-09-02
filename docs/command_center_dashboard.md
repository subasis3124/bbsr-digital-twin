# Bhubaneswar Digital Twin — Command-Center Dashboard (Phase 14)

## Architecture Overview

The Phase 14 Command-Center Dashboard provides an integrated, map-centric decision-support portal for urban intelligence, what-if scenario simulations, and emergency resource optimization in Bhubaneswar.

```
                  +-----------------------------------+
                  |   React + TypeScript Frontend     |
                  |     (Vite, Leaflet, Lucide)       |
                  +-----------------+-----------------+
                                    |
                    REST API Calls  | (Proxied via Vite)
                                    v
                  +-----------------+-----------------+
                  |      FastAPI Aggregation Layer    |
                  |     (/api/v1/dashboard/summary)   |
                  +-----------------+-----------------+
                                    |
           +------------------------+------------------------+
           |                        |                        |
           v                        v                        v
+--------------------+   +--------------------+   +--------------------+
|  City State Engine |   | Simulation Engine  |   | Optimization Engine|
| (PostGIS & Models) |   |  (Counterfactual)  |   | (OR-Tools Flow)    |
+--------------------+   +--------------------+   +--------------------+
```

## Key Dashboard Capabilities

1. **Map-Centric Telemetry Visualization**:
   - Leaflet dark-theme base map centered at Bhubaneswar coordinates (`[20.296, 85.824]`).
   - Dynamic GeoJSON rendering for Flood Risk Grid Cells, GNN Traffic Road Segments, Air Quality Monitoring Stations, Ward Boundaries, Base Roads, Bus Stops, Bus Routes, and Water Bodies.
   - Click-to-inspect Spatial Inspector drawer providing real-time entity telemetry.

2. **City State Summary KPI Panel**:
   - Live aggregated key performance indicators covering flood risk distribution, average traffic speed, PM2.5 air quality levels, and emergency infrastructure counts.

3. **What-If Simulation Counterfactual Interface**:
   - Interactive configuration forms for Heavy Rainfall, Road Network Closure, Air Pollution Surge, and Emergency Demand Surge.
   - Modeled impact summary comparing base state vs simulated counterfactual state.

4. **Emergency Optimization Decision Support**:
   - Solves OR-Tools min-cost capacitated flow for resource allocation (Hospitals, Police, Fire Stations).
   - Dynamic map overlay displaying directional flow vectors from demand incidents to assigned facilities.
   - Benchmarks optimization performance against nearest-resource heuristics.

5. **Scientific Provenance Disclosures & Validation Warnings**:
   - Every panel, map feature, and inspection card clearly discloses data provenance: `OBSERVED STATE`, `FORECAST STATE`, `COUNTERFACTUAL STATE`, or `SYNTHETIC STATE`.
   - Explicit warnings for synthetic baseline integrations and non-dispatch advisory recommendations.

## API Contracts Used

- `GET /api/v1/dashboard/summary`: Aggregated city metrics and system health.
- `GET /api/v1/city-state/metadata`: Canonical city state engine metadata.
- `GET /api/v1/flood-risk`: Geospatial flood risk predictions and SHAP feature attributions.
- `GET /api/v1/gnn/traffic`: Graph Neural Network road segment speed forecasts.
- `GET /api/v1/air-quality`: Multi-station air quality forecasts.
- `GET /api/v1/hospitals`, `police`, `fire-stations`, `wards`, `roads`: GeoJSON infrastructure features.
- `POST /api/v1/simulations`: Trigger scenario simulation runs.
- `POST /api/v1/optimization/emergency`: Trigger emergency resource allocation solvers.

## How to Run the Frontend Locally

### Prerequisites
- Node.js (v18+ recommended)
- Python 3.10+ virtualenv with backend dependencies installed

### Running Backend API
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Running Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:3000`.

### Running Frontend Unit Tests
```bash
cd frontend
npm test
```
