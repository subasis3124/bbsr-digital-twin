# Bhubaneswar Digital Twin — Demonstration Guide & AI Examples

This document presents a structured **5–10 minute demonstration script** of the **Bhubaneswar Digital Twin** system and provides **15 verified natural language AI example prompts**.

---

## 🎬 5–10 Minute Demonstration Script

### DEMO 1: Open Command Center & Overview
- **Action**: Launch the web app at `http://localhost:5173`.
- **Narration / Display**:
  - Show top KPI header: Active City Indicator snapshot, Average Air Quality (PM2.5), Average Traffic Speed, High Flood-Risk Cell Count.
  - Show 2D Leaflet interactive map with municipal ward boundaries, road networks, hospitals, and water bodies.
  - Toggle layers via the Layer Control Panel (Wards, Roads, Hospitals, Schools, Bus Stops, Water Bodies).

---

### DEMO 2: Query Flood Risk Layer
- **Action**: In the Natural Language AI Panel, type:
  > `"Show high flood-risk areas."`
- **Behind the Scenes**:
  - AI Intent Classifier → `FLOOD_QUERY`
  - Tool Invoked → `get_flood_risk(risk_level="HIGH")`
  - Map Action → Filters spatial grid cell overlay to highlight cells where predicted flood probability > 0.6.
- **Narration**: Point out spatial clusters near Lowland Wards and drainage basins. Note the data provenance warning ("Synthetic model training data").

---

### DEMO 3: Inspect Traffic Forecasts
- **Action**: In the AI Panel, type:
  > `"Show traffic forecasts for the next hour."`
- **Behind the Scenes**:
  - AI Intent Classifier → `TRAFFIC_QUERY`
  - Tool Invoked → `get_gnn_traffic(forecast_horizon_minutes=60)`
  - Map Action → Highlights road segments with predicted speeds and congestion ratios.
- **Narration**: Demonstrate spatio-temporal GNN prediction on major arterial roads (e.g. Janpath, NH-16).

---

### DEMO 4: Switch to 3D GIS View
- **Action**: Click the **"3D View"** toggle button in the top navigation header.
- **Display**:
  - CesiumJS 3D terrain and extruded 3D building geometries appear.
  - Flood risk surface renders as an elevated blue spatial polygon plane.
  - Traffic road networks overlay in 3D space with color-coded speed metrics.
  - Click on a 3D building to inspect height and structural attributes in the Spatial Inspector.

---

### DEMO 5: Run Heavy Rainfall What-If Simulation
- **Action**: Return to 2D/3D view and enter prompt:
  > `"Run heavy rainfall simulation with 120mm rainfall."`
- **Behind the Scenes**:
  - AI Intent Classifier → `SIMULATION_RUN`
  - Tool Invoked → `run_simulation(scenario_type="heavy_rainfall", parameters={"rainfall_intensity_mm": 120.0})`
- **Narration**:
  - Highlight **Baseline vs Counterfactual Scenario**.
  - Show updated impact summary: `affected_spatial_units_count`, `high_risk_cells`, `infrastructure_impacted`.
  - Explain base-state immutability: the underlying PostgreSQL database state remains uncorrupted.

---

### DEMO 6: Run Emergency Resource Optimization
- **Action**: Enter prompt:
  > `"Optimize emergency resources for this flood scenario."`
- **Behind the Scenes**:
  - AI Intent Classifier → `OPTIMIZATION_RUN`
  - Tool Invoked → `run_emergency_optimization(resource_types=["hospital"], method="ortools_min_cost_flow", simulation_id="<active_sim_id>")`
- **Narration**:
  - Google OR-Tools solver allocates response units from nearest available healthcare facilities.
  - Compare **Baseline (Nearest Facility)** vs **Optimized Flow**: reduced travel time and zero facility capacity overload.
  - *Disclaimer*: Emphasize decision support nature — this does not dispatch real-world emergency vehicles.

---

### DEMO 7: Ask AI for Scenario Explanation
- **Action**: Enter prompt:
  > `"What changed under the scenario?"`
- **Behind the Scenes**:
  - Tool Invoked → `get_simulation_result`
  - AI queries the actual simulation output metrics from the Digital Twin engine rather than generating generic text.
- **Narration**: Show how the LLM synthesizes exact numerical delta figures (e.g. +34% flooded area, 12 roads submerged) into plain English explanations.

---

## 🤖 15 Verified AI Example Prompts

| # | User Natural Language Prompt | Target AI Tool | Primary Map / Response Action |
| :--- | :--- | :--- | :--- |
| **1** | `"Show high flood-risk areas."` | `get_flood_risk` | Highlights grid cells with `risk_level="HIGH"`. |
| **2** | `"Which roads have the lowest predicted traffic speed?"` | `get_gnn_traffic` | Filters road segments sorted by lowest speed. |
| **3** | `"Show AQI around this area."` | `get_air_quality` | Displays air quality stations and PM2.5 pollutant levels. |
| **4** | `"Which hospitals are near these high-risk areas?"` | `get_hospitals` | Overlays healthcare facilities in Wards with active flood alerts. |
| **5** | `"What happens under heavy rainfall?"` | `run_simulation` | Triggers 100mm heavy rainfall scenario simulation. |
| **6** | `"Compare the current state with this scenario."` | `get_simulation_result` | Computes delta breakdown between base state and active scenario. |
| **7** | `"Close Janpath road and show the traffic impact."` | `run_simulation` | Executes `road_closure` scenario on specified segment ID. |
| **8** | `"Optimize emergency resources under this scenario."` | `run_emergency_optimization` | Executes OR-Tools capacitated vehicle allocation solver. |
| **9** | `"Show this in 3D."` | `switch_view_mode` | Switches viewport to CesiumJS 3D mode. |
| **10** | `"Why is this area classified as high risk?"` | `get_flood_risk` | Displays SHAP feature importance breakdown (elevation, slope, NDWI). |
| **11** | `"Show all police stations in Ward 12."` | `get_police_stations` | Filters police facilities by `ward_id=12`. |
| **12** | `"Show fire stations across Bhubaneswar."` | `get_fire_stations` | Displays all fire station point vector features. |
| **13** | `"What is the city state overview?"` | `get_city_state` | Fetches aggregated multi-domain state metadata and ward summaries. |
| **14** | `"Show transit bus routes."` | `get_bus_routes` | Displays CRUT public transit route linestrings. |
| **15** | `"Give me a summary of city KPIs."` | `get_dashboard_summary` | Returns top-level summary metrics for header cards. |
