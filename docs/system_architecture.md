# Bhubaneswar Digital Twin — System Architecture

This document describes the high-level architecture, design principles, data flow, and component interactions of the **Bhubaneswar Digital Twin** system.

---

## 🏛️ High-Level System Architecture

The system follows a modular, multi-tier architecture separating data ingestion, spatial storage, urban state management, machine learning, counterfactual simulation, decision optimization, natural language orchestration, and 2D/3D visualization.

```mermaid
graph TD
    User["👤 USER / URBAN PLANNER"] --> Dashboard["🖥️ COMMAND CENTER DASHBOARD (React + Vite)"]
    Dashboard --> Visualization2D["🗺️ Leaflet 2D GIS Layer"]
    Dashboard --> Visualization3D["🌐 CesiumJS 3D GIS Layer"]
    Dashboard --> AIInterface["🤖 NATURAL LANGUAGE AI INTERFACE"]
    
    AIInterface -->|Intent & Tool Dispatch| Services["⚡ DIGITAL TWIN API SERVICES (FastAPI)"]
    Dashboard -->|REST Requests| Services
    
    Services --> CityState["🏙️ UNIFIED CITY STATE ENGINE"]
    Services --> MLModule["🔮 ML FORECASTING (Flood, Traffic, AQI, GNN)"]
    Services --> SimEngine["🌧️ WHAT-IF SIMULATION ENGINE"]
    Services --> OptEngine["🚑 EMERGENCY RESOURCE OPTIMIZATION"]
    
    CityState --> Database[("🗄️ POSTGIS SPATIAL DATABASE (PostgreSQL + PostGIS)")]
    MLModule --> Database
    SimEngine --> Database
    OptEngine --> Database
    
    Database <-- ETL["🔄 ETL & INGESTION PIPELINES"]
    ETL <-- ExternalData["🌐 EXTERNAL DATA SOURCES (OSM, DEM, OpenMeteo, CPCB, Infrastructure)"]
```

---

## 🧩 Component Subsystems

### 1. Frontend & Command Center (`frontend/`)
- **Technology**: React 18, TypeScript, Vite, Tailwind CSS / Vanilla CSS.
- **Components**:
  - **KPI Panel**: Real-time city metrics (AQI, traffic speed, flood alert grid count, active scenarios).
  - **Layer Controls**: Toggle vector infrastructure (Wards, Roads, Hospitals, Schools, Bus Routes, Water Bodies).
  - **2D GIS Viewer**: Leaflet map displaying vector layers, choropleths, and emergency routes.
  - **3D GIS Viewer**: CesiumJS rendering 3D terrain, building extrusions, flood elevation planes, and flow vectors.
  - **Spatial Inspector**: Contextual telemetry for selected vector features.
  - **AI Command Panel**: Natural language query input, tool execution logs, and provenance explanations.

### 2. Backend & API Services (`backend/app/`)
- **Technology**: FastAPI, Python 3.10+, Pydantic V2, SQLAlchemy 2.0.
- **Responsibility**: Exposes spatial GeoJSON endpoints, handles simulation runs, executes emergency optimization solvers, coordinates AI tool calls, and returns structured data with data provenance metadata.

### 3. Spatial Database Layer (`database/`, `backend/app/models.py`)
- **Technology**: PostgreSQL 15+ with PostGIS 3.3 extension, Alembic migrations.
- **Responsibility**: Persists spatial entities using EPSG:4326 (WGS84), spatial indexing (GIST), temporal observation tables, simulation run logs, and optimization assignments.

### 4. Unified City State Engine (`ml/city_state/`, `backend/app/routes/city_state.py`)
- **Responsibility**: Provides a canonical, queryable representation of urban indicators across spatial units (Wards & Spatial Grid Cells). Computes dynamic aggregates across traffic, flood, and AQI domains.

### 5. Machine Learning Suite (`ml/`)
- **Flood Risk Model**: Random Forest classifier using DEM elevation, slope, and NDWI water indices.
- **Traffic Speed Forecaster**: Ridge & XGBoost regression models for road segment speed predictions.
- **Air Quality Forecaster**: Multi-pollutant forecaster (PM2.5, PM10, NO2, etc.).
- **Graph Neural Network (GNN)**: PyTorch GraphSAGE / GCN model operating over the road network graph topology.

### 6. What-If Simulation Engine (`ml/simulation/`)
- **Responsibility**: Implements counterfactual scenario simulations (Heavy Rainfall, Road Closures, Pollution Spikes) while guaranteeing immutable base state integrity. Computes spatial impact summaries and severity metrics.

### 7. Emergency Resource Optimization Engine (`ml/optimization/`)
- **Technology**: Google OR-Tools (Capacitated Vehicle & Assignment Solver).
- **Responsibility**: Provides decision support for allocating emergency response units (ambulances, rescue teams, fire engines) to affected demand locations under simulated disaster conditions.

### 8. Natural Language AI Interface (`backend/app/ai/`)
- **Responsibility**: Intent classification and tool orchestration through a controlled tool registry (`TOOL_REGISTRY`). Translates user queries into validated map actions and analytics API queries.

---

## 🔄 End-to-End Data Flow

1. **Ingestion Flow**: Data Sources → ETL Pipelines → PostGIS Database (Vector & Raster Feature Extraction).
2. **State & Analytics Flow**: PostGIS → City State Engine → ML Models / GNN → API Endpoints → Frontend Command Center.
3. **Simulation-Optimization Flow**: User Request / AI Query → Simulation Engine (Counterfactual Transformation) → Emergency Optimization Solver → API Response → 2D/3D GIS Rendering.
