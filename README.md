# Bhubaneswar Digital Twin 🏙️🌊🚦

An integrated urban digital-twin decision-support architecture for **Bhubaneswar, Odisha, India**. The system combines spatial PostGIS infrastructure, automated ETL data ingestion, multi-domain machine learning (Flood, Traffic, Air Quality, GNN), counterfactual What-If simulations, emergency resource optimization, a 2D/3D GIS command center dashboard, and a natural language AI interface.

---

## 🌟 Key Capabilities

- **🗺️ 2D & 3D GIS Visualization**: Dual-engine rendering using **Leaflet** (2D vector layers) and **CesiumJS** (3D terrain, building extrusions, elevated flood planes).
- **🌊 Flood Risk Modeling**: Random Forest classification using DEM topography, slope, and Sentinel-2 NDWI remote sensing imagery.
- **🚦 Traffic & GNN Forecasting**: Spatio-Temporal Graph Neural Network (ST-GNN) predicting speed propagation and congestion across road network graphs.
- **🌬️ Air Quality Forecasting**: Multi-pollutant forecaster predicting ambient $PM_{2.5}$ and AQI categories across municipal monitoring stations.
- **🏙️ Unified City State Engine**: Aggregates dynamic indicators into a queryable urban state across wards and 500m spatial grid cells.
- **🌧️ What-If Simulation Engine**: Counterfactual scenario execution (Heavy Rainfall, Road Closures, Air Pollution, Emergency Demand Surges) with base-state immutability.
- **🚑 Emergency Resource Optimization**: Google OR-Tools capacitated vehicle allocation solver matching emergency resources to urban demand points under simulated stress.
- **🤖 Natural Language AI Interface**: Intent classification and tool orchestration over a controlled tool registry (`TOOL_REGISTRY`), translating natural language into map actions and analytics.
- **🛡️ Scientific Provenance & Safeguards**: Comprehensive data lineage tracking, synthetic data labeling, and strict temporal/spatial leakage prevention.

---

## 🏛️ System Architecture

```mermaid
graph TD
    User["👤 URBAN PLANNER / OPERATOR"] --> Dashboard["🖥️ COMMAND CENTER DASHBOARD (React + Vite)"]
    Dashboard --> Leaflet2D["🗺️ Leaflet 2D GIS Layer"]
    Dashboard --> Cesium3D["🌐 CesiumJS 3D GIS Layer"]
    Dashboard --> AIInterface["🤖 AI INTERFACE (Controlled Tool Registry)"]
    
    AIInterface --> Services["⚡ DIGITAL TWIN FASTAPI SERVICES"]
    Dashboard --> Services
    
    Services --> CityState["🏙️ UNIFIED CITY STATE ENGINE"]
    Services --> MLModule["🔮 ML FORECASTING (Flood, Traffic, AQI, GNN)"]
    Services --> SimEngine["🌧️ WHAT-IF SIMULATION ENGINE"]
    Services --> OptEngine["🚑 EMERGENCY RESOURCE OPTIMIZATION"]
    
    CityState --> PostGIS[("🗄️ POSTGIS SPATIAL DATABASE")]
    MLModule --> PostGIS
    SimEngine --> PostGIS
    OptEngine --> PostGIS
    
    PostGIS <-- ETL["🔄 ETL INGESTION PIPELINES (OSM, DEM, OpenMeteo, CPCB)"]
```

---

## 💻 Technology Stack

- **Core / Backend**: Python 3.10+, FastAPI, Pydantic V2, Uvicorn, SQLAlchemy 2.0.
- **Database & Spatial**: PostgreSQL 15+, PostGIS 3.3+, GeoAlchemy2, Shapely, GeoPandas, Alembic.
- **Machine Learning & Graph**: PyTorch, PyTorch Geometric, scikit-learn, XGBoost, Google OR-Tools, MLflow.
- **Frontend Dashboard**: React 18, TypeScript, Vite, Leaflet, CesiumJS, Tailwind CSS / Vanilla CSS.
- **Containerization & CI/CD**: Docker, Docker Compose, Pytest (163 tests), Vitest (14 tests).

---

## 🔬 Scientific Integrity & Validation Disclaimer

> [!IMPORTANT]
> **Distinction Between Software Validation & Scientific Validation**:
> - **Software System Validation**: The software architecture, API contracts, PostGIS database schema, simulation state immutability, GNN graph determinism, and UI responsiveness have been systematically verified via automated test suites.
> - **Scientific Ground Truth**: Model outputs (flood probabilities, speed forecasts, AQI concentrations) represent **statistical model estimates**, not absolute ground truth.
> - **Synthetic Datasets**: Synthetic datasets used for pipeline integration testing do not constitute empirical field validation against sensor networks.
> - **Simulation & Optimization**: Simulations are **counterfactual scenarios** for decision support. Emergency resource optimizations provide decision support recommendations and do not dispatch real emergency response units.
> - **AI Interface**: The AI layer functions purely as an orchestration and explanation layer querying the Digital Twin engine; it is **not** an autonomous source of facts.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python `3.10+` (Tested on `3.13.5`)
- Node.js `v18+` (Tested on `v22.17.0`)
- PostgreSQL `15+` with PostGIS `3.3+` (or Docker)

### 2. Clone & Install Dependencies
```bash
# Clone repository
git clone https://github.com/subasis3124/bbsr-digital-twin.git
cd bbsr-digital-twin

# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### 3. Environment & Database Setup
```bash
# Configure environment
cp .env.example .env

# Initialize PostGIS database (or run via docker-compose up -d db)
createdb -U postgres bbsr_digital_twin
psql -U postgres -d bbsr_digital_twin -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Apply database migrations
alembic -c backend/alembic.ini upgrade head
```

### 4. Run Application
```bash
# Terminal 1: Launch Backend API (http://localhost:8000)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Launch Frontend Dashboard (http://localhost:5173)
cd frontend
npm run dev
```

---

## 🧪 Running Tests

```bash
# Backend Test Suite (163 tests)
pytest tests/ -v

# Frontend Test Suite (14 tests)
cd frontend
npm test -- --run

# Production Build Verification
npm run build
```

---

## 🐳 Docker Deployment

To launch the full containerized stack (PostGIS DB, FastAPI Backend, React Frontend, MLflow):

```bash
docker-compose up --build -d
```
- Dashboard: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`
- MLflow: `http://localhost:5000`

---

## 📍 Data Provenance Summary

- **OSM & BMC Vector Infrastructure**: Real spatial geometries for wards, roads, hospitals, schools, and transit stops.
- **SRTM DEM & Slope**: Real topographic raster elevation sampled at spatial grid cell centroids.
- **Sentinel-2 Remote Sensing**: Real satellite-derived NDWI water index measurements.
- **OpenMeteo Weather**: Real meteorological observations and forecast feeds.
- **Traffic & Air Quality Telemetry**: Synthetic fallback profiles calibrated for integration testing.

---

## 🗺️ Project Roadmap Status

All 18 planned project roadmap phases are **COMPLETE**:

1. [x] Repository Setup & Architecture Baseline
2. [x] PostgreSQL + PostGIS Schema Design
3. [x] Bhubaneswar GIS Data Ingestion
4. [x] Vector Infrastructure Ingestion
5. [x] Reusable ETL Pipelines
6. [x] Flood Risk Modeling
7. [x] Flood Risk Prediction Map
8. [x] Traffic Forecasting
9. [x] Air Quality Forecasting
10. [x] Graph Neural Network Traffic Forecasting
11. [x] Unified City State Engine
12. [x] What-If Simulation Engine
13. [x] Emergency Resource Optimization
14. [x] Command-Center Dashboard
15. [x] 3D GIS Integration
16. [x] Natural Language AI Interface
17. [x] Comprehensive System Testing
18. [x] Documentation & Deployment Preparation

---

## 📚 Documentation Index

- [System Architecture](docs/system_architecture.md)
- [Setup & Installation Guide](docs/setup.md)
- [Environment Configuration](docs/configuration.md)
- [REST API Reference](docs/api.md)
- [Demonstration & AI Guide](docs/demo_guide.md)
- [Data Provenance Specification](docs/data_provenance.md)
- [ML Model Cards](docs/model_cards.md)
- [What-If Simulation Engine](docs/simulation_engine.md)
- [Emergency Resource Optimization](docs/emergency_resource_optimization.md)
- [Natural Language AI Interface](docs/natural_language_ai_interface.md)
- [Comprehensive Testing Report](docs/comprehensive_testing.md)
- [Operations & Maintenance Manual](docs/operations.md)

---

## 📄 License & Attribution

This software repository is maintained for the **Bhubaneswar Digital Twin** decision-support project. For commercial reuse or licensing inquiries, please contact the project owner.
