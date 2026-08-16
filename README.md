# BBSR Digital Twin — AI-Powered Urban Intelligence & Simulation Platform

BBSR Digital Twin is a data-driven urban intelligence and simulation platform for the city of Bhubaneswar, Odisha, India. The platform integrates real-world GIS vector data, satellite raster data, climate indicators, and real-time transit telemetry to simulate urban phenomena, predict pluvial flood risks, and optimize resource allocation during crises.

---

## 🏗️ Architecture Overview

The system is built on a service-oriented architecture:
1. **Frontend**: Next.js (App Router), React, TypeScript, Tailwind CSS, Zustand, Recharts, MapLibre GL JS (for 2D GIS), and CesiumJS (for 3D GIS).
2. **Backend**: Python, FastAPI, Pydantic, GeoPandas, Rasterio, Shapely.
3. **Database**: PostgreSQL with PostGIS extension for spatial queries.
4. **Machine Learning**: NumPy, Pandas, Scikit-learn, XGBoost, PyTorch, PyTorch Geometric, MLflow.
5. **Optimization**: Google OR-Tools.
6. **Infrastructure**: Docker & Docker Compose.

---

## 📁 Repository Structure

```text
bbsr-digital-twin/
├── frontend/         # Next.js, React, MapLibre GL, CesiumJS
├── backend/          # FastAPI REST API, routing, simulation engine
├── ml/               # Machine Learning training models (XGBoost, PyTorch)
├── data/             # Spatial data (raw, interim, processed)
│   ├── raw/
│   ├── interim/
│   └── processed/
├── pipelines/        # Reusable ETL pipeline code (gis, weather, population, etc.)
├── database/         # Database migrations, seed scripts, SQL definitions
├── notebooks/        # Jupyter research notebooks for EDA and ML baselines
├── experiments/      # MLflow configuration and training tracking
├── docs/             # Architecture, schema, and API documentation
├── tests/            # Automated test suites (API, pipelines, validation)
└── docker/           # Dockerfiles and Docker Compose files
```

---

## 🚀 Quickstart

### Prerequisites
- **Docker** and **Docker Compose** installed.
- **Node.js** (v18+) & **npm** (for local frontend development).
- **Python** (v3.11) (for local backend development).

### 1. Configure Environment
Copy the environment variables template and customize it:
```bash
cp .env.example .env
```

### 2. Start PostgreSQL + PostGIS & MLflow
Run the database and experiment tracking containers:
```bash
docker compose -f docker/docker-compose.yml up -d
```

### 3. Verify services
- PostgreSQL/PostGIS will listen on port `5432`.
- MLflow dashboard will be accessible at [http://localhost:5000](http://localhost:5000).

---

## 📚 Project Roadmap

- **Phase 1**: Repository and Architecture Setup (Current)
- **Phase 2**: PostgreSQL + PostGIS schema and index design
- **Phase 3**: Bhubaneswar geographic data ingestion
- **Phase 4**: 2D Interactive map frontend implementation
- **Phase 5**: Reusable ingestion pipelines (weather, population, satellite)
- **Phase 6**: ML Flood Risk model training (XGBoost / Random Forest)
- **Phase 7**: Flood Risk visual map integration
- ... (Refer to [ROADMAP.md](ROADMAP.md) for full details).
