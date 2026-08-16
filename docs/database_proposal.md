# BBSR Digital Twin — PostgreSQL + PostGIS Schema Proposal

This document outlines the proposed database structure for Phase 2. We use standard geometries in WGS 84 (`SRID 4326`) for map compatibility, and we project to UTM Zone 45N (`SRID 32645`) for metric analysis when writing pipelines.

---

## 🏛️ Administrative & Infrastructure Tables

### 1. City Boundary
```sql
CREATE TABLE city (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT 'Bhubaneswar',
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_city_geom ON city USING GIST(geom);
```

### 2. Wards
```sql
CREATE TABLE wards (
    id SERIAL PRIMARY KEY,
    ward_number INT NOT NULL UNIQUE,
    name VARCHAR(150),
    population_est INT,
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_wards_geom ON wards USING GIST(geom);
```

### 3. Road Network
```sql
CREATE TABLE roads (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    name VARCHAR(200),
    highway_type VARCHAR(50), -- e.g., primary, secondary, residential
    lanes INT DEFAULT 1,
    maxspeed INT,
    oneway BOOLEAN DEFAULT FALSE,
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_roads_geom ON roads USING GIST(geom);
```

### 4. Buildings
```sql
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    building_type VARCHAR(100), -- residential, commercial, school, etc.
    height NUMERIC,
    levels INT,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_buildings_geom ON buildings USING GIST(geom);
```

### 5. Critical Infrastructure Points (Hospitals, Schools, Bus Stops)
```sql
CREATE TABLE hospitals (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    name VARCHAR(250) NOT NULL,
    beds INT DEFAULT 0,
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_hospitals_geom ON hospitals USING GIST(geom);

CREATE TABLE schools (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    name VARCHAR(250) NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_schools_geom ON schools USING GIST(geom);

CREATE TABLE bus_stops (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    name VARCHAR(250),
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bus_stops_geom ON bus_stops USING GIST(geom);

CREATE TABLE bus_routes (
    id SERIAL PRIMARY KEY,
    route_name VARCHAR(100) NOT NULL,
    operator VARCHAR(100) DEFAULT 'CRUT', -- Capital Region Urban Transport
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bus_routes_geom ON bus_routes USING GIST(geom);
```

### 6. Water Bodies
```sql
CREATE TABLE water_bodies (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    name VARCHAR(150),
    water_type VARCHAR(50), -- reservoir, lake, river, pond
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_water_bodies_geom ON water_bodies USING GIST(geom);
```

---

## 🌦️ Sensor and Observation Tables

### 7. Weather
```sql
CREATE TABLE weather (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    temperature NUMERIC, -- in Celsius
    rainfall NUMERIC,    -- hourly precip in mm
    humidity NUMERIC,
    wind_speed NUMERIC,
    is_forecast BOOLEAN DEFAULT FALSE,
    source VARCHAR(100) NOT NULL
);
CREATE INDEX idx_weather_timestamp ON weather(timestamp);
```

### 8. Air Quality
```sql
CREATE TABLE air_quality (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    pm25 NUMERIC,
    pm10 NUMERIC,
    co NUMERIC,
    no2 NUMERIC,
    so2 NUMERIC,
    o3 NUMERIC,
    aqi_value INT,
    geom GEOMETRY(Point, 4326) NOT NULL,
    source VARCHAR(100) NOT NULL
);
CREATE INDEX idx_air_quality_timestamp ON air_quality(timestamp);
CREATE INDEX idx_air_quality_geom ON air_quality USING GIST(geom);
```

### 9. Traffic Speed Observations
```sql
CREATE TABLE traffic (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    road_id INT REFERENCES roads(id) ON DELETE CASCADE,
    observed_speed INT NOT NULL, -- in km/h
    congestion_ratio NUMERIC,    -- current_speed / freeflow_speed
    source VARCHAR(100) NOT NULL
);
CREATE INDEX idx_traffic_timestamp ON traffic(timestamp);
CREATE INDEX idx_traffic_road_id ON traffic(road_id);
```

### 10. Population Grids
```sql
CREATE TABLE population (
    id SERIAL PRIMARY KEY,
    population_count INT NOT NULL,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_population_geom ON population USING GIST(geom);
```

### 11. Historical Flood Events
```sql
CREATE TABLE flood_events (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(150),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    severity VARCHAR(50), -- Minor, Moderate, Major
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_flood_events_geom ON flood_events USING GIST(geom);
```

---

## 🛰️ Remote Sensing & Machine Learning tables

### 12. Spatial Grid Cells (Uniform Grid for ML Features)
```sql
CREATE TABLE spatial_grid_cells (
    id SERIAL PRIMARY KEY,
    cell_code VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'BBSR-100m-X12-Y45'
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    centroid GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_spatial_grid_cells_geom ON spatial_grid_cells USING GIST(geom);
```

### 13. Satellite Derived Features
```sql
CREATE TABLE satellite_features (
    id SERIAL PRIMARY KEY,
    cell_id INT REFERENCES spatial_grid_cells(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    elevation NUMERIC,  -- from DEM
    slope NUMERIC,      -- from DEM
    ndvi NUMERIC,       -- Normalized Difference Vegetation Index
    ndwi NUMERIC,       -- Normalized Difference Water Index
    ndbi NUMERIC,       -- Normalized Difference Built-Up Index
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_satellite_features_cell_time ON satellite_features(cell_id, timestamp);
```

### 14. ML Model Predictions
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    cell_id INT REFERENCES spatial_grid_cells(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL, -- e.g., 'flood_risk_xgboost'
    model_version VARCHAR(50) NOT NULL, -- e.g., 'v1.0.3'
    prediction_time TIMESTAMP WITH TIME ZONE NOT NULL,
    predicted_probability NUMERIC NOT NULL,
    predicted_class VARCHAR(50) NOT NULL, -- e.g., 'HIGH'
    feature_importance_shap JSONB -- SHAP explanation map for why this prediction was made
);
CREATE INDEX idx_predictions_cell ON predictions(cell_id);
```

### 15. Scenario Simulations
```sql
CREATE TABLE simulations (
    id SERIAL PRIMARY KEY,
    simulation_uuid UUID NOT NULL,
    scenario_name VARCHAR(100) NOT NULL, -- e.g., 'monsoon_rain_plus_50'
    triggered_by VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cell_id INT REFERENCES spatial_grid_cells(id) ON DELETE CASCADE,
    baseline_class VARCHAR(50) NOT NULL,
    simulated_class VARCHAR(50) NOT NULL,
    delta_risk NUMERIC NOT NULL
);
CREATE INDEX idx_simulations_uuid ON simulations(simulation_uuid);
```
