# Phase 15: 3D GIS Integration — Bhubaneswar Digital Twin

## 1. Overview
Phase 15 extends the **Bhubaneswar Digital Twin** command-center dashboard from a 2D Leaflet mapping system into a full **3D Geospatial Intelligence (GIS) Environment** powered by **CesiumJS**, **Resium**, and **Vite**.

The 3D implementation provides true 3D spatial analysis rather than decorative visuals:
- **True 3D Geospatial Extrusion**: Polygon building footprints and flood risk grid cells are extruded into true 3D geometries based on elevation and real/exemplary physical height data.
- **Topographical Terrain**: Real-world elevation model integrated using Cesium Terrain providers.
- **3D Telemetry Inspection**: Full spatial picking and telemetry inspection capability matching Phase 14 2D functionality.
- **Seamless 2D/3D Mode Switching**: Live state and layer selection are preserved when toggling between 2D Map and 3D City mode in the header navigation.

---

## 2. System Architecture

```
                                 ┌──────────────────────────────────────────┐
                                 │            TopHeader Controls            │
                                 │   [ 🗺️ 2D MAP ]   │   [ 🌐 3D CITY ]     │
                                 └────────────────────┬─────────────────────┘
                                                      │ (viewMode State)
                                                      ▼
                            ┌──────────────────────────────────────────────────┐
                            │               Command Center App                 │
                            └─────────┬──────────────────────────────┬─────────┘
                                      │                              │
                    (viewMode === '2D')                              (viewMode === '3D')
                                      ▼                              ▼
                          ┌──────────────────────┐      ┌──────────────────────────┐
                          │   CommandMap (2D)    │      │     City3DView (3D)      │
                          │   (Leaflet Engine)   │      │    (CesiumJS Engine)     │
                          └──────────────────────┘      └────────────┬─────────────┘
                                                                     │
                                                      ┌──────────────┴──────────────┐
                                                      ▼                             ▼
                                           ┌────────────────────┐      ┌──────────────────────┐
                                           │  Cesium Entities   │      │  Spatial Inspector   │
                                           │ (Extruded 3D Mesh) │      │  (Entity Picking)    │
                                           └────────────────────┘      └──────────────────────┘
```

---

## 3. 3D Spatial Layer Specifications

| Layer | Geometry | 3D Visualization Strategy | Provenance / Extrusion Specs |
|---|---|---|---|
| **Building Footprints** | 3D Polygon | 3D Polygon Extrusion (`extrudedHeight`) | Real building height (m) or `levels * 3.5m`. Defaults to `12m` exemplary height with relative extrusion indicator. |
| **Flood Risk Grid** | 3D Polygon | Probability Height Extrusion (`prob * 80m + 10m`) | Categorical color-coding (Green = Low, Amber = Medium, Red = High/Very High). Counterfactual simulation overrides active during What-If runs. |
| **GNN Traffic Network** | 3D Polyline | Elevated Polylines | Speed-based color gradient (Green ≥40km/h, Yellow 20-40km/h, Red <20km/h). Closed roads rendered as thick red vectors during simulations. |
| **Air Quality** | 3D Column | 3D Cylinder Height & AQI Color | Height proportional to pollutant concentration (`val * 6m + 50m`). Purple glowing columns for telemetry stations. |
| **Emergency Facilities** | 3D Marker | Vertical Service Cylinders | Color-coded by type (Red = Hospital, Blue = Police, Orange = Fire Station). |
| **Emergency Allocations** | 3D Arc | Curved 3D Polyline Arc | 3D Bezier trajectory from demand origin cell to assigned facility, displaying travel time and capacity metrics. |
| **Wards & Boundary** | 3D Polygon | Semi-transparent Base Polygon | Purple boundary outline with 15% fill transparency. |

---

## 4. Mode Switching & State Preservation
The command center maintains a unified state model across modes:
- **Shared Layer Control**: Active layer toggles (e.g. toggling Flood Risk or Traffic) update both 2D and 3D views instantaneously.
- **Shared Selection Context**: Selecting an entity in 3D opens the same `SpatialInspector` side drawer as in 2D.
- **Shared Temporal & Counterfactual Context**: Forecast horizon selection (+1h to +24h), active What-If simulation counterfactuals, and Emergency Optimization allocation arcs seamlessly transfer into 3D view space.

---

## 5. Provenance & Scientific Validation Indicators
- **Extrusion Provenance**: Buildings lacking height or level metadata display a **"Relative Exemplary Extrusion (12m default)"** tag in the Spatial Inspector.
- **Synthetic Data Indicators**: When baseline or fallback synthetic datasets are rendered in 3D, appropriate `SYNTHETIC FALLBACK` badges and warnings remain visible.
- **Counterfactual Overlay**: Active What-If simulation scenarios render floating warning banners in the bottom left of the 3D viewport.

---

## 6. Performance Optimization & Graceful Degradation

### WebGL Fallback Handling
- Before initializing the Cesium JS canvas, `City3DView` tests for WebGL context support via `isWebGLSupported()`.
- If WebGL is unavailable or fails to initialize:
  1. A user-friendly error message is displayed.
  2. A **"Return to 2D Command Center"** action button allows immediate fallback.
  3. The system log captures the initialization failure.

### Entity & Render Optimization
- **Dynamic Entity Purging**: Cesium entities are managed via standard React `useEffect` hooks, clearing and updating only when active layer configuration or temporal state changes.
- **Selective Level of Detail**: Extruded polygons use efficient Cartesian polygon hierarchies for crisp render performance at 60 FPS.

---

## 7. Automated Testing Suite

- **Vitest Unit Tests**: Validate 3D view component mounting, layer configuration propagation, and graceful WebGL fallback handling (`frontend/src/test/City3DView.test.tsx`).
- **Production Build**: Verified clean TypeScript compilation and asset bundling via `vite-plugin-cesium`.
- **Backend Integrity**: All 124 backend API tests continue to pass without regression.
