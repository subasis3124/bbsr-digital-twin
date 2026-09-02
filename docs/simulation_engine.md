# Phase 12 — What-If Simulation Engine Documentation
**Bhubaneswar Digital Twin Project**

## 1. Overview & Architecture

The **What-If Simulation Engine** provides a formal scenario abstraction framework for applying hypothetical counterfactual perturbations to baseline city states without modifying or overwriting original data.

### Core Mathematical Pattern:
$$\text{BaseState} + \text{Scenario}(\theta) \xrightarrow{\mathcal{S}} \text{SimulatedState} + \text{ImpactSummary}$$

where:
- $\text{BaseState}$ is the canonical urban state derived from the Unified City State Engine (`CityStateAggregator`).
- $\text{Scenario}(\theta)$ defines strongly-typed perturbation parameters and spatial/temporal boundary filters.
- $\mathcal{S}$ is the simulation engine executing discrete propagation steps across environmental, hazard, mobility, infrastructure, and derived layers.
- $\text{SimulatedState}$ is a newly generated `CityState` payload marked as synthetic.
- $\text{ImpactSummary}$ contains quantitative metrics deltas, unit-level deltas, and macro severity ratings.

---

## 2. Immutability & Provenance Guarantees

1. **Strict Base-State Immutability**:
   - Baseline city state Pydantic objects are deep-copied prior to transformation. Original database records and cached snapshots remain 100% unaltered.
2. **Provenance & Warnings**:
   - Every simulated state payload sets `is_synthetic = True`, `data_provenance_status = "scenario_simulation"`, and appends the explicit scientific warning:
     > `"WARNING: This result is a scenario perturbation and is not a calibrated physical simulation."`
3. **Inspectable Dependency Graph**:
   - Every simulation run tracks step-by-step transformation steps (`TransformationStep`) with explicit inputs, outputs, methods, and dependency edges.

---

## 3. Supported Scenarios & Parameter Definitions

### 3.1 Heavy Rainfall Scenario (`heavy_rainfall`)
- **Inputs**:
  - `rainfall_multiplier` (float, default: `1.0`): Scale factor for baseline rainfall.
  - `rainfall_delta_mm` (float, default: `0.0`): Additive rainfall in mm.
  - `duration_hours` (float, default: `1.0`): Event duration.
  - `spatial_scope` (SpatialScope): Boundary filter.
- **Propagation Chain**:
  1. `rainfall_sim = base_rainfall * multiplier + delta_mm`
  2. `flood_risk_probability` recalculated based on rainfall intensity threshold (e.g., >50mm => flood risk >= 0.75).
  3. `road_accessibility = max(0.0, 1.0 - flood_risk_probability)`
  4. `observed_speed = base_speed * road_accessibility`
  5. `congestion_ratio = min(2.0, base_congestion * (1.0 + 1.5 * flood_risk_probability))`

### 3.2 Road Closure Scenario (`road_closure`)
- **Inputs**:
  - `closed_road_ids` (List[int]): List of road IDs to close.
  - `closure_duration_hours` (float, default: `2.0`): Duration of closure.
  - `rerouting_capacity_factor` (float, default: `0.5`): Detour absorption factor.
- **Propagation Chain**:
  1. Closed segments set `road_accessibility = 0.0`, `observed_speed = 0.0`, `status = "CLOSED"`.
  2. Surrounding detour corridors experience a surge in `congestion_ratio` and drop in `observed_speed`.

### 3.3 Air Pollution Event Scenario (`air_pollution`)
- **Inputs**:
  - `pollutant` (str, default: `"pm25"`): `pm25`, `pm10`, `no2`, `co`, `so2`, `o3`.
  - `multiplier` (float, default: `1.0`): Concentration multiplier.
  - `delta` (float, default: `0.0`): Additive delta.
- **Propagation Chain**:
  1. Pollutant concentration perturbed.
  2. AQI sub-index and air quality category (`GOOD`, `MODERATE`, `UNHEALTHY`, `VERY_UNHEALTHY`, `HAZARDOUS`) updated.

### 3.4 Emergency Demand Surge Scenario (`emergency_demand`)
- **Inputs**:
  - `hospital_demand_multiplier` (float, default: `1.5`): Surge multiplier.
  - `incident_count_surge` (int, default: `5`): Additional incident count.
- **Propagation Chain**:
  1. `emergency_service_density` recalculated to reflect stress on emergency facilities.

---

## 4. FastAPI Endpoints (`/api/v1/simulations`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/simulations/scenarios/types` | Lists supported scenario types and JSON schema requirements. |
| `POST` | `/api/v1/simulations` | Executes a What-If simulation and returns the complete result payload. |
| `GET` | `/api/v1/simulations` | Lists historical persisted simulation runs. |
| `GET` | `/api/v1/simulations/{id}` | Retrieves full simulation detail by `simulation_id` (UUID). |
| `GET` | `/api/v1/simulations/{id}/impact` | Retrieves impact metrics, deltas, and macro severity. |
| `GET` | `/api/v1/simulations/{id}/state` | Retrieves simulated city states as a GeoJSON `FeatureCollection`. |

---

## 5. CLI Pipeline Runner

Execute simulations directly from the command line:

```bash
# Heavy Rainfall Simulation
python -m pipelines.simulation --scenario-type heavy_rainfall --parameters '{"rainfall_multiplier": 1.5, "rainfall_delta_mm": 30.0}' --output rainfall_sim.json

# Road Closure Simulation
python -m pipelines.simulation --scenario-type road_closure --parameters '{"closed_road_ids": [101, 102]}' --dry-run
```

---

## 6. Test Suite & Validation

All 16 dedicated simulation unit and integration tests in `tests/test_simulation.py` verify:
- Scenario schema validation & parameter bounds checking
- Heavy rainfall, road closure, air pollution, and emergency demand propagation logic
- Inspectability of transformation dependency graphs
- Quantitative impact metric delta calculations & severity classification
- Spatial scope filtering (bbox, grid cell, ward, road)
- Prevention of temporal leakage (`simulation_timestamp >= base_timestamp`)
- Synthetic provenance and scientific warning injection
- Base-state immutability
- Deterministic simulation outputs
- FastAPI route responses & CLI execution

Total workspace tests passing: **105/105** (0 failures).
