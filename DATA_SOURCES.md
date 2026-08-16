# Bhubaneswar Digital Twin — Data Sources Catalog

To build a technically credible and data-driven digital twin, we list here the exact datasets, formats, accessibility statuses, update frequencies, and licenses.

---

## 🗺️ Administrative and GIS Base Data

### 1. Ward Boundaries (Bhubaneswar Municipal Corporation - BMC)
*   **Accessibility**: Immediately Accessible
*   **Source**: [DataMeet Indian Municipal Spatial Data GitHub](https://github.com/datameet/Municipal_Spatial_Data) or BhubaneswarOne GIS portal (scraped / public GeoJSON).
*   **Format**: GeoJSON (EPSG:4326)
*   **License**: Creative Commons Attribution-ShareAlike 2.5 India (DataMeet community curated).

### 2. Road Network and Infrastructure Points of Interest (POIs)
*   **Components**: Road centerlines (line geometries), hospitals (points), schools (points), bus stops (points).
*   **Accessibility**: Immediately Accessible
*   **Source**: OpenStreetMap (OSM) via Overpass Turbo API (`overpass-api.de`).
*   **Query Example**:
    ```text
    [out:json][timeout:25];
    area["name"="Bhubaneswar"]->.searchArea;
    (
      node["amenity"="hospital"](area.searchArea);
      way["amenity"="hospital"](area.searchArea);
    );
    out body; >; out skel qt;
    ```
*   **Format**: GeoJSON (EPSG:4326)
*   **License**: Open Database License (ODbL) (Requires attribution to "OpenStreetMap contributors").

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
