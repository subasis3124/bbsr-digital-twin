# Bhubaneswar Digital Twin — Operations & Maintenance Manual

This manual documents operational procedures for database backups, schema migration, logging, health monitoring, service restarts, and model file management for the **Bhubaneswar Digital Twin** system.

---

## 🗄️ Database Backup & Recovery

### 1. Database Backup Procedure (`pg_dump`)
To export a complete custom-format backup of the PostGIS database:

```bash
# Automated export to custom format (.dump)
pg_dump -U postgres -h localhost -p 5432 -F c -b -v -f "bbsr_digital_twin_$(date +%Y%m%m_%H%M%S).dump" bbsr_digital_twin
```

To create a plain SQL script backup:
```bash
pg_dump -U postgres -h localhost -p 5432 -F p -v -f "bbsr_digital_twin_schema_data.sql" bbsr_digital_twin
```

> [!NOTE]
> Ensure PostGIS spatial tables (e.g. `spatial_ref_sys`) are included or recreated cleanly during restore.

### 2. Database Restore Procedure (`pg_restore`)
To restore from a custom-format dump (`.dump`) into a fresh database:

```bash
# 1. Create target database
createdb -U postgres -h localhost -p 5432 bbsr_digital_twin_restored

# 2. Enable PostGIS extension
psql -U postgres -d bbsr_digital_twin_restored -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 3. Restore dump
pg_restore -U postgres -h localhost -p 5432 -d bbsr_digital_twin_restored -v "bbsr_digital_twin_backup.dump"
```

---

## 🔄 Database Migration Lifecycle

All database schema modifications are tracked using **Alembic**.

### Apply Upward Migrations:
```bash
alembic -c backend/alembic.ini upgrade head
```

### Rollback Migration:
```bash
alembic -c backend/alembic.ini downgrade -1
```

### Create New Migration Revision:
```bash
alembic -c backend/alembic.ini revision --autogenerate -m "describe_schema_change"
```

---

## 🔍 Health Checks & Monitoring

The system exposes a lightweight operational health endpoint at `GET /health`.

### Health Check Request
```bash
curl -X GET http://localhost:8000/health
```

### Expected Response
```json
{
  "status": "healthy",
  "database": "connected",
  "postgis": "available",
  "postgis_version": "POSTGIS=\"3.3.2\""
}
```

### Operational Status Codes
- `200 OK`: API and PostGIS database connection are operational.
- `503 SERVICE UNAVAILABLE`: Database connection or PostGIS check failed.

---

## 🪵 Logging & Observability

### 1. Application Logs
FastAPI logs HTTP request routes, status codes, exception traces, and execution times to stdout/stderr.
In Docker environments, view logs via:
```bash
docker-compose -f docker/docker-compose.yml logs -f backend
```

### 2. ETL Ingestion Logs
ETL pipelines output structured log messages documenting record counts, data provenance flags, and API connection retries.

### 3. MLflow Experiment Logs
Machine learning training metrics, spatial cross-validation scores, and model parameters are logged to the MLflow tracking server at `http://localhost:5000` (or `sqlite:///mlflow.db`).

---

## 🔄 Service Restarts & Routine Maintenance

### Restart Backend Service
```bash
# Uvicorn standalone restart
pkill -f uvicorn
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Docker Compose restart
docker-compose -f docker/docker-compose.yml restart backend
```

### Model Artifact Management
Trained ML weights and scikit-learn/PyTorch model files are stored under `models/`. When updating model binaries:
1. Validate new model output with `pytest tests/test_phase17_ml_models.py`.
2. Update version identifiers in `models/manifest.json` (if present) or pipeline config.
3. Reload backend API service to load updated model checkpoints into memory.
