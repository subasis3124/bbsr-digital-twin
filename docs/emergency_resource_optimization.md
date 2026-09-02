# Phase 13 — Emergency Resource Optimization System

## Overview
The **Emergency Resource Optimization Engine** in the Bhubaneswar Digital Twin provides autonomous decision-support for emergency resource allocation (hospitals, police stations, fire stations) under baseline and simulated urban stress conditions (e.g. heavy rainfall flood risk or road closures).

The system integrates **Google OR-Tools** (Capacitated Min-Cost Flow / MILP formulation) to compute optimal facility assignments that minimize global travel cost while respecting capacity and network accessibility constraints.

---

## Architecture & Data Flow

```
                                +---------------------------+
                                |  CityState Snapshots      |
                                |  (Base or What-If Sim)    |
                                +-------------+-------------+
                                              |
                                              v
+----------------------------+   +------------+------------+   +----------------------------+
|  Emergency Demand Points   |-->|   Travel Cost Calculator |<--|   Emergency Infrastructure |
|  (Wards / Grid Cells)      |   |   (Haversine + Penalty)  |   |   (Hospitals / Stations)   |
+----------------------------+   +------------+------------+   +----------------------------+
                                              |
                                              v
                                 +------------+------------+
                                 |  OR-Tools Min-Cost Flow |
                                 |  Optimization Engine    |
                                 +------------+------------+
                                              |
                                              v
                                 +------------+------------+
                                 | Baseline Benchmark &    |
                                 | Decision Explainability |
                                 +------------+------------+
                                              |
                                              v
                                 +------------+------------+
                                 | OptimizationRun Model   |
                                 | (PostgreSQL / JSONB)    |
                                 +-------------------------+
```

---

## Mathematical Formulation

### Objective Function
The engine minimizes total weighted spatial travel cost and unserved demand penalties:

$$\min \sum_{i \in \text{Demands}} \sum_{j \in \text{Facilities}} (c_{ij} \cdot w_i + \varepsilon \cdot j) \cdot x_{ij} + P_{\text{unserved}} \cdot \sum_{i \in \text{Demands}} u_i$$

Where:
- $x_{ij} \in \mathbb{Z}_{\ge 0}$: Quantity of emergency cases from demand point $i$ assigned to facility $j$.
- $u_i \in \mathbb{Z}_{\ge 0}$: Unserved demand quantity at location $i$.
- $c_{ij}$: Effective travel cost (Haversine distance divided by facility accessibility $A_j$).
- $w_i$: Priority weight ($3.0$ for `CRITICAL`, $1.5$ for `HIGH`, $1.0$ for `NORMAL`).
- $\varepsilon$: Deterministic tie-breaker epsilon ($10^{-6} \cdot j$).
- $P_{\text{unserved}}$: High penalty for unserved demand ($10000.0$).

### Constraints
1. **Demand Satisfaction**:
   $$\sum_{j} x_{ij} + u_i = d_i \quad \forall i$$
2. **Facility Capacity**:
   $$\sum_{i} x_{ij} \le C_j \quad \forall j \text{ with known capacity}$$
3. **Inaccessibility Constraint**:
   $$x_{ij} = 0 \quad \text{if } A_j \le 0.05 \text{ or facility is inaccessible}$$

---

## Key Components

### 1. Engine & Modules (`ml/optimization/`)
- `schemas.py`: Pydantic models for demand, resources, allocations, constraints, and provenance.
- `resources.py`: Extracts hospital, police, and fire station capacities and status from PostGIS database models or `CityState` payloads. Missing bed counts default to `unknown` with scenario-defined operational caps.
- `demand.py`: Generates standardized demand points from ward population estimates or simulated surges.
- `travel_cost.py`: Calculates Haversine distance matrix with accessibility penalty factors.
- `solver.py`: Formulates and executes OR-Tools CBC/GLOP solver deterministically.
- `baseline.py`: Nearest Available Resource baseline solver for performance benchmark comparison.
- `explanation.py`: Computes allocation deltas and decision provenance between base and simulated states.
- `engine.py`: Core coordinator class `EmergencyOptimizationEngine`.

### 2. Database Model (`backend/app/models.py`)
- `OptimizationRun`: Table storing optimization metadata, JSONB allocations, baseline benchmark comparisons, and simulation impact deltas.

### 3. FastAPI Endpoints (`backend/app/routes/optimization.py`)
- `POST /api/v1/optimization/emergency`: Execute optimization.
- `GET /api/v1/optimization/emergency`: List historical optimization runs.
- `GET /api/v1/optimization/emergency/{run_id}`: Retrieve run detail by UUID.
- `GET /api/v1/optimization/emergency/{run_id}/allocations`: Retrieve assignment breakdown.
- `GET /api/v1/optimization/emergency/{run_id}/impact`: Compare optimized results vs baseline & simulation impact.
- `GET /api/v1/optimization/resources`: Query available emergency facilities.

### 4. CLI Runner (`pipelines/optimize_emergency.py`)
```bash
# Run emergency hospital optimization (dry-run)
python -m pipelines.optimize_emergency --resource-type hospital --dry-run

# Run scenario optimization with DB persistence
python -m pipelines.optimize_emergency --simulation-id <UUID> --save
```

---

## Scientific Provenance & Safety Warning
All optimization outputs include mandatory provenance metadata:
- `is_synthetic`: `True`
- `engine_version`: `"1.0.0"`
- `decision_support_warning`: `"NOTICE: This is a model-based decision-support optimization tool. All allocations are scenario estimates intended for emergency planning and must be verified by operational command."`
