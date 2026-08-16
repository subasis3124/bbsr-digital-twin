# Bhubaneswar Digital Twin — Database Layer Documentation

This document describes the PostgreSQL/PostGIS database design, SQLAlchemy models, migration configuration, spatial design choices, and management commands.

---

## 🏛️ Database Architecture & Flow

The BBSR Digital Twin utilizes **Postgres** with the **PostGIS** spatial extension as its data warehouse. The backend maps tables to Python models using **SQLAlchemy** (Object Relational Mapper) and deploys changes using **Alembic** migrations.

```text
FastAPI Endpoint 
   ↓ (Dependency injection)
get_db() -> yields SQLAlchemy Session 
   ↓
SQLAlchemy Engine (Connection Pool)
   ↓
PostgreSQL / PostGIS Database (Docker Container)
```

---

## 🐋 Docker Container Configuration

Running database instances inside Docker prevents the user from needing to manually compile and install PostGIS binaries on Windows. 

The configuration in `docker/docker-compose.yml` deploys the official `postgis/postgis:15-3.3` image:
- **Port Mapping**: `5432:5432`
- **Volume Mount**: Maps `postgres_data` volume to `/var/lib/postgresql/data` for persistent storage.
- **Health Check**: Executes `pg_isready` to block dependent containers until the database is ready.

---

## 🗺️ Spatial Design Concepts

### 1. What is PostGIS?
PostgreSQL stores standard numbers and text. PostGIS adds spatial columns (`GEOMETRY`) and functions. It enables the database to answer questions like:
- "Is this point inside this ward boundary?"
- "What is the distance between this road and this water body?"
- "What is the slope of this cell grid?"

### 2. Geometry Types Used
- **Point**: Represents single POIs with $X, Y$ coordinates (e.g., `hospitals`, `schools`, `bus_stops`).
- **LineString**: Ordered set of vertices representing paths (e.g., `roads`, `bus_routes`).
- **Polygon**: A closed ring representing areas (e.g., `buildings`, `water_bodies`, `spatial_grid_cells`).
- **MultiPolygon**: A collection of polygons representing discontinuous boundaries (e.g., `wards`, `city`).

### 3. Coordinate Reference Systems (CRS)
- **EPSG:4326 (WGS 84)**: Used for coordinates stored in degrees (Latitude/Longitude). Standard for web layers (MapLibre GL JS/CesiumJS).
- **EPSG:32645 (WGS 84 / UTM Zone 45N)**: Used for calculating metrics (meters) like distances or grid cell areas. Projected locally during feature calculations.

### 4. Spatial Indexing
Traditional indexes (B-Trees) only sort elements in one dimension. Spatial queries require indexing bounding boxes in two dimensions. We use **GIST (Generalized Search Tree)** indexes:
```sql
CREATE INDEX idx_wards_geom ON wards USING GIST(geom);
```
GIST indexes speed up polygon intersections (`ST_Contains`, `ST_Intersects`, `ST_DWithin`) by orders of magnitude.

---

## 🗄️ Database Tables Schema

Refer to [docs/database_proposal.md](database_proposal.md) for full SQL definitions. The SQLAlchemy mappings are defined in [backend/app/models.py](file:///d:/AITwin_City/backend/app/models.py).

### Core Entities & Relationships

| Component | Table Name | Geometry Type | Key Fields & Relationships |
| :--- | :--- | :--- | :--- |
| **City** | `city` | Polygon | Name, center boundary |
| **Wards** | `wards` | MultiPolygon | Ward number, name, estimated population |
| **Roads** | `roads` | LineString | OSM ID, speed, lanes. Has relationship to `traffic` |
| **Hospitals** | `hospitals` | Point | Name, beds count |
| **Water Bodies** | `water_bodies`| Polygon | Water type (river, pond, lake) |
| **Weather** | `weather` | None (Relational)| Precipitation (rainfall), temp, timestamp |
| **Air Quality** | `air_quality` | Point | PM2.5, PM10, AQI index, station location |
| **Grid Cells** | `spatial_grid_cells`| Polygon | Cell code, centroid point. Has relationships to `predictions` & `simulations` |
| **ML Predictions**| `predictions` | None (Relational)| FK to cell. Predicted risk class, probability, SHAP map |
| **Simulations** | `simulations` | None (Relational)| FK to cell. Simulation UUID, scenario, delta risk |

---

## 🔄 Database Migrations (Alembic)

Migrations keep track of schema changes as the database structure evolves.

### Why Alembic?
Instead of manually dropping and recreating tables during development (which destroys existing data), Alembic acts as "version control" for your database tables.

### Execution Workflow

1. **Configure Environment variables**:
   Create a local `.env` containing database credentials.
2. **Upgrade to Latest Schema**:
   Deploys migrations up to the latest state.
   ```powershell
   alembic upgrade head
   ```
3. **Generate a New Migration (Autogenerate)**:
   Compares SQLAlchemy metadata in `models.py` with current PostGIS schema and writes DDL scripts.
   ```powershell
   alembic revision --autogenerate -m "add index to traffic table"
   ```
4. **Downgrade / Revert Last Migration**:
   Rolls back the last run database migration.
   ```powershell
   alembic downgrade -1
   ```

---

## 🧪 Testing Commands

To run automated checks:
```powershell
# Activate local python environment
.\.venv\Scripts\Activate.ps1

# Run tests
python -m pytest tests/
```
These verify config schemas, ORM attributes, and API route serialization using mock sessions.
