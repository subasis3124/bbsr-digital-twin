# Bhubaneswar Digital Twin — Data Sources Catalog

To build a technically credible and data-driven digital twin, we list here the exact datasets, formats, accessibility statuses, update frequencies, and licenses.

---

## 🗺️ Administrative and GIS Base Data

### 1. Ward Boundaries (Bhubaneswar Municipal Corporation - BMC)
*   **Accessibility**: Immediately Accessible
*   **Source**: [DataMeet Indian Municipal Spatial Data GitHub](https://github.com/datameet/Municipal_Spatial_Data) or BhubaneswarOne GIS portal (scraped / public GeoJSON).
*   **Format**: GeoJSON (EPSG:4326)
*   **License**: Creative Commons Attribution-ShareAlike 2.5 India (DataMeet community curated).

### 2. Road Network (OSM Centerlines)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 19,315 ways read; 14,825 ways geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way ID) -> `roads.osm_id`
    - `name` (Road name) -> `roads.name`
    - `highway` (Type category, e.g., primary, residential) -> `roads.highway_type`
    - `lanes` (Parsed count) -> `roads.lanes` (defaults to 1 if absent/invalid)
    - `maxspeed` (Cleaned speed limit km/h) -> `roads.maxspeed`
    - `oneway` (Boolean status) -> `roads.oneway`
*   **Limitations**: Lanes and maxspeed values are sparsely tagged in OSM for certain residential and minor roads; default values are safely fallback-mapped.

### 3. Building Footprints (OSM Footprints)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 22,723 elements read; 21,322 elements geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Relation ID) -> `buildings.osm_id`
    - `building` (Type category, e.g., apartments, commercial) -> `buildings.building_type` (defaults to "yes")
    - `height` (Parsed float value in meters) -> `buildings.height`
    - `building:levels` (Parsed integer levels count) -> `buildings.levels`
*   **Limitations**: Height and building:levels are sparsely populated on OSM; missing values are correctly loaded as NULL in the database without fabrication. Complex MultiPolygon relations are normalized to the largest component Polygon to ensure `osm_id` uniqueness and schema conformance.

### 4. Healthcare Facilities (OSM POIs)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 224 elements read; 209 elements geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Node/Relation ID) -> `hospitals.osm_id`
    - `name` (Healthcare facility name) -> `hospitals.name` (strictly required, empty names skipped)
    - `beds` / `healthcare:beds` (Parsed bed count) -> `hospitals.beds`
*   **Limitations**: Bed counts are sparsely populated in OSM; missing values are loaded as NULL in the database without fabrication. Polygon boundaries (e.g., hospital campuses) are normalized to their centroid Point geometries.

### 5. Educational Facilities (OSM POIs)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 70 elements read; 61 elements geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Node/Relation ID) -> `schools.osm_id`
    - `name` (Institution name) -> `schools.name` (strictly required, empty names skipped)
    - `amenity` (Institution type, e.g. school, university, college) -> `schools.institution_type` (defaults to "school")
*   **Limitations**: Polygon boundaries (e.g., school/college campus boundaries) are normalized to their centroid Point geometries to conform with the POINT database schema.

### 6. Emergency & Public Safety Infrastructure (OSM POIs)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**:
    - Police stations: 5 elements read; 4 elements geographically relevant and ingested into database.
    - Fire stations: 2 elements read; 1 element geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Node/Relation ID) -> `police_stations.osm_id` / `fire_stations.osm_id`
    - `name` (Facility name) -> `police_stations.name` / `fire_stations.name` (strictly required, empty names skipped)
*   **Limitations**: Polygon campus outlines (e.g., station building polygons) are normalized to their centroid Point geometries to conform with the POINT database schemas.

### 7. Bus Stops & Public Transit (OSM POIs)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 34 elements read; 34 elements geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Node/Relation ID) -> `bus_stops.osm_id`
    - `name` (Bus stop name) -> `bus_stops.name` (stored as `NULL` if missing or empty in OSM)
*   **Limitations**: Polygon campus outlines (e.g., station building polygons) are normalized to their centroid Point geometries to conform with the POINT database schemas.

### 8. Hydrological Infrastructure / Water Bodies (OSM Vector)
*   **Source**: OpenStreetMap (OSM) contributors via Overpass API (`https://overpass-api.de/api/interpreter`).
*   **Extraction Date**: 2026-08-22
*   **Geographic Scope**: Bhubaneswar bounding box `[20.211, 85.732, 20.367, 85.904]`, spatially filtered by BMC ward boundaries.
*   **Number of Features**: 65 elements read; 46 elements geographically relevant and ingested into database.
*   **CRS**: EPSG:4326 (WGS 84 coordinate system).
*   **License**: Open Database License (ODbL). Requires the attribution: "© OpenStreetMap contributors".
*   **Attribute Mapping**:
    - `id` (OSM Way/Relation ID) -> `water_bodies.osm_id`
    - `name` (Water body name) -> `water_bodies.name` (stored as `NULL` if missing or empty in OSM)
    - `water` / `waterway` / `landuse` / `natural` (Category type) -> `water_bodies.water_type` (defaults to "water" if absent)
*   **Limitations**: Relation multi-polygons are resolved to the largest component Polygon by area to satisfy the database POLYGON geometry constraint.

---

## ⛰️ Terrain & Environmental Data

### 3. Digital Elevation Model (DEM)
*   **Accessibility**: Immediately Accessible
*   **Source**: Copernicus DEM (GLO-30) / SRTM (Shuttle Radar Topography Mission) 30m.
*   **Format**: GeoTIFF (raster grid)
*   **License**: Open / Public Domain.

### 4. Satellite Imagery & Indices (NDVI, NDWI, NDBI)
*   **Accessibility**: Immediately Accessible
*   **Source**: Copernicus Sentinel-2 / Landsat 8-9 (accessed via Google Earth Engine or USGS EarthExplorer).
*   **Format**: Cloud-Optimized GeoTIFF (COG)
*   **Use Cases**:
    *   **NDVI** (Normalized Difference Vegetation Index) for land cover and vegetation density.
    *   **NDWI** (Normalized Difference Water Index) for surface water body detection.
    *   **NDBI** (Normalized Difference Built-Up Index) for building/urban concrete density.
*   **License**: Open access for research and commercial reuse.

---

## 🌦️ Meteorological & Climate Data

### 5. Weather (Historical and Forecasts)
*   **Accessibility**: Requires API/Authentication
*   **Source**:
    *   **ERA5 Reanalysis**: Historical gridded climate indicators (Copernicus Climate Change Service).
    *   **NASA POWER API**: Hourly meteorological parameters (solar radiation, precipitation).
    *   **Open-Meteo API**: Non-commercial API for real-time/forecast meteorology.
    *   **IMD FMO**: India Meteorological Department reports (manual/scraped PDF forecasts).
*   **Format**: JSON/NetCDF
*   **License**: Copernicus License / NASA open data policy.

---

## 🚦 Urban Operations (Traffic, AQI, Population)

### 6. Air Quality (AQI, PM2.5, PM10)
*   **Accessibility**: Immediately Accessible
*   **Source**: OpenAQ API / Central Pollution Control Board (CPCB) India portal (National Air Quality Index).
*   **Station Locations**: Bhubaneswar has active CPCB monitoring stations (e.g., Patrapada, IRC Village).
*   **Format**: JSON / CSV
*   **License**: Government Open Data License - India (GODL).

### 7. Population & Demographics
*   **Accessibility**: Immediately Accessible
*   **Source**: WorldPop (100m resolution gridded population data) / Census of India 2011 (Ward level).
*   **Format**: GeoTIFF (gridded) / CSV (tabular attributes)
*   **License**: Creative Commons Attribution 4.0 International (WorldPop).

### 8. Traffic Telemetry
*   **Accessibility**: Uncertain / Requires API
*   **Source**: Real-time traffic telemetry is proprietary. We will:
    1. Query OSM `maxspeed` and road capacity tags.
    2. Interface with TomTom/Here Traffic API if API keys are available.
    3. Generate a structured traffic profile (using typical rush-hour functions mapped to the road network graph nodes) to serve as a **synthetic traffic simulator**, clearly marked as synthetic.
*   **License**: Proprietary / OpenStreetMap data derivatives.

---

## 🏷️ Summary Matrix

| Data Source | Parameter | Access Level | Format | Integration Path |
| :--- | :--- | :--- | :--- | :--- |
| **DataMeet GitHub** | Ward Boundaries | Immediately Accessible | GeoJSON | DB Ingestion script in Phase 3 |
| **OpenStreetMap** | Roads, POIs, Schools | Immediately Accessible | GeoJSON | Overpass API script in Phase 3 |
| **Copernicus GLO-30**| Terrain/Elevation | Immediately Accessible | GeoTIFF | Raster processing in Phase 5 |
| **Sentinel-2** | Land Cover (NDVI) | Immediately Accessible | GeoTIFF | GEE Export / Rasterio in Phase 5 |
| **OpenAQ / CPCB** | AQI PM2.5 / PM10 | Immediately Accessible | JSON API | Scheduled pipeline in Phase 5 |
| **Open-Meteo** | Temperature/Rainfall | Immediately Accessible | JSON API | Scheduled pipeline in Phase 5 |
| **WorldPop** | Population Density | Immediately Accessible | GeoTIFF | Spatial zonal stats in Phase 5 |
| **Traffic Sensors** | Congestion/Speed | Uncertain / Synthetic | JSON API | Custom Simulation Engine in Phase 8 |
