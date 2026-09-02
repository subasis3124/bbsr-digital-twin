# Bhubaneswar Digital Twin — Setup & Installation Guide

This document provides a step-by-step setup guide for setting up, configuring, running, testing, and building the **Bhubaneswar Digital Twin** system from a fresh repository clone.

---

## ⚙️ System Prerequisites

Before starting, ensure your host environment meets the following software requirements:

| Component | Minimum Version | Verified / Recommended Version | Note |
| :--- | :--- | :--- | :--- |
| **Operating System** | Linux, macOS, or Windows 10/11 | Windows 11 / Ubuntu 22.04 | Cross-platform |
| **Python** | `3.10` | `3.11` / `3.13.5` | Required for backend, ML, ETL |
| **Node.js** | `v18.0.0` | `v20.x` / `v22.17.0` | Required for frontend dashboard |
| **npm** | `v9.0.0` | `v10.x` | Node package manager |
| **PostgreSQL** | `15.0` | `15.x` | Database engine |
| **PostGIS** | `3.3` | `3.3+` | Spatial database extension |
| **Git** | `2.30.0+` | Latest | Version control |

---

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/subasis3124/bbsr-digital-twin.git
cd bbsr-digital-twin
```

---

### Step 2: Set Up Python Virtual Environment
Create and activate a Python virtual environment at the repository root:

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

### Step 3: Install Python Dependencies
Upgrade `pip` and install all required backend, spatial, ML, and testing packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Install Frontend Dependencies
Navigate to the `frontend` directory and install JavaScript/TypeScript packages:

```bash
cd frontend
npm install
cd ..
```

---

### Step 5: Configure Environment Variables
Copy the template `.env.example` file to `.env` at the project root:

**Linux / macOS / PowerShell:**
```bash
cp .env.example .env
```

Review `.env` and verify database parameters:
```env
POSTGRES_DB=bbsr_digital_twin
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_secure_pwd
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

### Step 6: Initialize PostgreSQL Database & PostGIS Extension
Make sure your PostgreSQL server is running (or start the PostGIS Docker container).

Create the target database and enable the PostGIS extension:

**Using psql CLI:**
```bash
psql -U postgres -c "CREATE DATABASE bbsr_digital_twin;"
psql -U postgres -d bbsr_digital_twin -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**Using Docker (Alternative):**
If you prefer running PostGIS inside Docker:
```bash
docker-compose -f docker/docker-compose.yml up -d db
```

---

### Step 7: Run Database Migrations
Apply all Alembic database schema migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

---

### Step 8: Start Backend Server
From the root directory, launch the FastAPI server using Uvicorn:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be accessible at:
- API Base URL: `http://localhost:8000/api/v1`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

### Step 9: Start Frontend Dashboard
Open a new terminal, navigate to `frontend`, and start Vite dev server:

```bash
cd frontend
npm run dev
```

The dashboard will open at `http://localhost:5173`.

---

## 🧪 Verification & Testing

### Run Backend Tests (`pytest`)
From the repository root:
```bash
pytest tests/ -v
```
*Expected Result*: All 163 backend tests pass.

### Run Frontend Tests (`vitest`)
From the `frontend/` directory:
```bash
cd frontend
npm test -- --run
```
*Expected Result*: All 14 frontend tests pass.

### Run Production Build
Verify production compilation:
```bash
cd frontend
npm run build
```
*Expected Result*: Builds distribution artifacts into `frontend/dist/` without errors.

---

## ⚠️ Common Setup Errors & Troubleshooting

### 1. `PostGIS extension not found`
- **Symptom**: `ERROR: extension "postgis" is not available`
- **Solution**: Install PostGIS package for your OS (e.g. `sudo apt-get install postgresql-15-postgis-3`) or use the official `postgis/postgis:15-3.3` Docker image.

### 2. `alembic: command not found`
- **Symptom**: `alembic` is not recognized.
- **Solution**: Ensure your virtual environment is activated (`source .venv/bin/activate` or `.\.venv\Scripts\Activate.ps1`).

### 3. `CORS Policy Error` in Browser Console
- **Symptom**: `Access to fetch at 'http://localhost:8000' from origin 'http://localhost:5173' has been blocked by CORS policy.`
- **Solution**: Ensure `ALLOWED_ORIGINS` in `.env` includes `http://localhost:5173` or is set to `*` in development mode.
