# BBSR Digital Twin — Implementation Roadmap

This document outlines the sequential phases of development. Every phase relies on the preceding ones. We will build, test, and verify each phase before moving forward.

---

```mermaid
graph TD
    Phase1[Phase 1: Architecture] --> Phase2[Phase 2: PostgreSQL/PostGIS Schema]
    Phase2 --> Phase3[Phase 3: Bhubaneswar GIS Data Ingestion]
    Phase3 --> Phase4[Phase 4: 2D GIS Map Dashboard]
    Phase4 --> Phase5[Phase 5: Automated Ingestion Pipelines]
    Phase5 --> Phase6[Phase 6: Flood Risk ML Training]
    Phase6 --> Phase7[Phase 7: Flood Risk Map Integration]
    Phase7 --> Phase8[Phase 8: Traffic Forecasting ML]
    Phase8 --> Phase9[Phase 9: AQI Forecasting ML]
    Phase9 --> Phase10[Phase 10: Graph Neural Network - GNN]
    Phase10 --> Phase11[Phase 11: City State Engine]
    Phase11 --> Phase12[Phase 12: What-if Simulation Engine]
    Phase12 --> Phase13[Phase 13: Resource Optimization]
    Phase13 --> Phase14[Phase 14: Command-Center Dashboard]
    Phase14 --> Phase15[Phase 15: 3D Digital Twin - CesiumJS]
    Phase15 --> Phase16[Phase 16: LLM Natural Language AI]
    Phase16 --> Phase17[Phase 17: Multi-layer Testing]
    Phase17 --> Phase18[Phase 18: Documentation]
```

---

## Detailed Phases

### Phase 1: Repository and Architecture (COMPLETE)
*   **Goal**: Setup folders, basic configurations, docker infrastructure, and base roadmap.
*   **Success Criteria**: All folders created, docker compose parses successfully, roadmap approved.

### Phase 2: PostgreSQL + PostGIS Schema Design (COMPLETE)
*   **Goal**: Create tables for administrative wards, OSM infrastructure, environmental readings, and ML predictions.
*   **Success Criteria**: SQL schema files written, spatial indexes created, migrations tested.

### Phase 3: Bhubaneswar GIS Ingestion (Current)
*   **Goal**: Automate downloading and validation of GIS data (Wards, Roads, POIs).
*   **Success Criteria**: Validated geometry inside PostGIS, zero duplicate errors, correct projection (EPSG:4326/32645).


### Phase 4: 2D Interactive Map
*   **Goal**: Render Bhubaneswar wards, roads, and POIs in a Next.js + MapLibre GL JS frontend.
*   **Success Criteria**: User can pan, zoom, click on wards, and see real metadata from PostGIS database.

### Phase 5: Reusable ETL Pipelines
*   **Goal**: Standardize ingestion pipelines (Weather, Air Quality, Population, NDVI).
*   **Success Criteria**: Logging for run times, records, and failures. Auto-ingests hourly/daily updates.

### Phase 6: First ML Problem — Flood Risk Modeling
*   **Goal**: Predict pluvial flood susceptibility using terrain (DEM), proximity to water, and land cover.
*   **Success Criteria**: XGBoost, Random Forest, and baseline models logged in MLflow with spatial train/test splits. Explainability computed via SHAP.

### Phase 7: Flood Risk Prediction Map
*   **Goal**: Run inference across grid cells and display LOW/MED/HIGH/VERY HIGH risks on the 2D map.
*   **Success Criteria**: Interactive cells display risk probabilities and SHAP feature importance on click.

### Phase 8: Traffic Forecasting
*   **Goal**: Use historical traffic profiles to predict road segment speeds.
*   **Success Criteria**: Regression models evaluating MAE and RMSE, avoiding lookahead data leakage.

### Phase 9: Air Quality Forecasting
*   **Goal**: Time-series forecasting for PM2.5/PM10.
*   **Success Criteria**: 6-hour, 12-hour, and 24-hour predictions using LSTM or XGBoost models.

### Phase 10: Graph Neural Network (GNN)
*   **Goal**: Translate road intersections into nodes and roads into edges for traffic forecasting.
*   **Success Criteria**: PyTorch Geometric implementation compared with non-graph traffic baselines.

### Phase 11: Unified City State Engine
*   **Goal**: Formulate a time-versioned `CityState` object representing all indicators at time $t$.
*   **Success Criteria**: Immutable database snapshots allowing retrieval of historic and current states.

### Phase 12: Simulation Engine (COMPLETE)
*   **Goal**: Run "what-if" scenarios (e.g., "increase rainfall by 50%", "close road segment X").
*   **Success Criteria**: Trigger ML inferences dynamically, support heavy rainfall, road closure, air pollution, emergency demand scenarios, maintain base-state immutability, enforce strict typing, log provenance warnings, expose FastAPI endpoints, and output inspectable delta differences (e.g., changes in hospital access and speed). All 105 tests passing.

### Phase 13: Emergency Resource Optimization (COMPLETE)
*   **Goal**: Solve facility capacity, dispatch, and supply distribution constraints using Google OR-Tools min-cost flow optimization.
*   **Success Criteria**: Implemented `OptimizationRun` model & Alembic migration; built `ml/optimization` module with OR-Tools CBC solver, Nearest Resource baseline benchmark, spatial travel cost matrix, demand surge generators, decision explainability, FastAPI endpoints `/api/v1/optimization/emergency`, CLI runner `pipelines.optimize_emergency`, and comprehensive test suite (123 total tests passing).

### Phase 14: Command-Center Dashboard (COMPLETE)
*   **Goal**: Build a polished, premium React + TypeScript command center dashboard providing map-centric visualizations, live city KPIs, what-if scenario simulations, and emergency resource optimization overlays.
*   **Success Criteria**: Integrated Vite + React + Leaflet frontend; built `/api/v1/dashboard/summary` FastAPI aggregation endpoint; implemented interactive map layers with bounding box support (Flood Risk, GNN Traffic, Air Quality, Wards, Emergency Resources, Allocation Overlays); added Spatial Inspector drawer; supported scenario simulation & OR-Tools emergency optimization triggers with baseline benchmarking; rendered scientific integrity provenance warnings & synthetic data disclosures; verified full test suite (124 backend tests + 9 frontend vitest tests passing).

### Phase 15: 3D GIS Integration (COMPLETE)
*   **Goal**: Render 3D terrain, extruded building footprints, 3D flood risk grids, elevated GNN traffic segments, AQI columns, and emergency allocation arcs using CesiumJS and Resium.
*   **Success Criteria**: Seamless 2D/3D view switching in top header navigation; 3D polygon building extrusion using observed height/level data with 12m exemplary defaults; 3D probability height extrusion for flood risk cells; 3D arc vectors for optimization allocations; spatial picking inspector for 3D entities; WebGL error detection with graceful fallback to 2D view; automated test suite (10 frontend Vitest tests + 124 backend tests passing) and documentation (`docs/3d_gis_integration.md`).

### Phase 16: Natural Language AI Interface
*   **Goal**: Add an LLM assistant using tool-calling to run simulations, compare traffic, and fetch risks.
*   **Success Criteria**: The LLM queries the database and ML APIs instead of fabricating numbers.

### Phase 17: Comprehensive Testing
*   **Goal**: Unit, integration, and ML data-leakage testing.
*   **Success Criteria**: All tests pass in the CI/CD pipeline.

### Phase 18: Documentation
*   **Goal**: Finalize architecture guides, ML model manuals, API documentation, and deployment guides.
*   **Success Criteria**: Fully documented codebase ready for research publication or field deployment.
