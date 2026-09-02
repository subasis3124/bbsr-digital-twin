# Bhubaneswar Digital Twin — Configuration Guide

This document details all environment variables supported by the **Bhubaneswar Digital Twin** backend, frontend, database, ETL, and AI subsystems.

---

## 🛠️ Configuration Overview

Configuration is managed dynamically via environment variables or a local `.env` file at the repository root. The backend utilizes `pydantic-settings` to load and validate variables at runtime.

> [!IMPORTANT]
> Never commit actual credentials, tokens, or private keys to version control. Use `.env.example` as a safe template.

---

## 📋 Environment Variables Reference Table

| Variable Name | Purpose | Required / Optional | Default Value | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `ENV` | Operational mode (`development`, `testing`, `production`) | Optional | `development` | `production` |
| `DEBUG` | Enables verbose FastAPI debugging and detailed error responses | Optional | `True` | `False` |
| `POSTGRES_DB` | Name of the PostGIS database | Required | `bbsr_digital_twin` | `bbsr_digital_twin_prod` |
| `POSTGRES_USER` | Database superuser/owner name | Required | `postgres` | `twin_app_user` |
| `POSTGRES_PASSWORD` | Database password | Required | `postgres_secure_pwd` | `s3cur3_p4ssw0rd!` |
| `POSTGRES_HOST` | Database host address or container hostname | Required | `localhost` | `db` |
| `POSTGRES_PORT` | PostgreSQL listening port | Required | `5432` | `5432` |
| `DATABASE_URL` | Complete SQLAlchemy database connection string | Optional (derived if omitted) | `None` | `postgresql://user:pass@db:5432/bbsr_digital_twin` |
| `BACKEND_HOST` | FastAPI host bind address | Optional | `0.0.0.0` | `127.0.0.1` |
| `BACKEND_PORT` | FastAPI server listening port | Optional | `8000` | `8000` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | Optional | `*` | `https://digitaltwin.bhubaneswar.gov.in,http://localhost:5173` |
| `MLFLOW_TRACKING_URI` | MLflow experiment tracking server URL or SQLite URI | Optional | `http://localhost:5000` | `sqlite:///mlflow.db` |
| `MAPBOX_ACCESS_TOKEN` | Mapbox Vector Tile access token | Optional | `your_mapbox_access_token_here` | `pk.eyJ1Ijo...` |
| `CESIUM_ION_ACCESS_TOKEN` | Cesium Ion access token for 3D terrain and building tilesets | Optional | `your_cesium_ion_access_token_here` | `eyJhbGciOi...` |
| `AI_PROVIDER` | AI Interface provider mode (`mock`, `openai`, `gemini`) | Optional | `mock` | `openai` |
| `AI_MODEL` | Target AI model identifier | Optional | `gpt-4o` | `gpt-4o-mini` |
| `OPENAI_API_KEY` | Secret API key for OpenAI API provider | Optional (Required if `AI_PROVIDER=openai`) | `your_openai_api_key_here` | `sk-proj-...` |
| `GEMINI_API_KEY` | Secret API key for Google Gemini API provider | Optional (Required if `AI_PROVIDER=gemini`) | `your_gemini_api_key_here` | `AIzaSy...` |
| `VITE_API_BASE_URL` | Frontend API client base URL | Optional | `http://localhost:8000/api/v1` | `https://api.digitaltwin.bhubaneswar.gov.in/api/v1` |
| `VITE_CESIUM_ION_TOKEN` | Public Cesium Ion access token for frontend 3D rendering | Optional | `your_cesium_ion_access_token_here` | `eyJhbGciOi...` |

---

## 🔒 Security Best Practices

1. **Production CORS**: In production, restrict `ALLOWED_ORIGINS` to the exact frontend domain(s). Avoid wildcard `*`.
2. **Secrets Management**: Use environment injection or secure secret stores (e.g. AWS Secrets Manager, HashiCorp Vault) rather than hardcoding `.env` files in production environments.
3. **Database Credentials**: Use dedicated database roles with minimum required privileges for production deployment.
