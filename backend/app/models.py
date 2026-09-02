from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from backend.app.database import Base

# 1. City Model
class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Bhubaneswar")
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 2. Ward Model
class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    ward_number = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(150))
    population_est = Column(Integer)
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 3. Road Model
class Road(Base):
    __tablename__ = "roads"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)  # OSM IDs can exceed standard integer size
    name = Column(String(200))
    highway_type = Column(String(50))
    lanes = Column(Integer, default=1)
    maxspeed = Column(Integer)
    oneway = Column(Boolean, default=False)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    traffic_observations = relationship("Traffic", back_populates="road", cascade="all, delete-orphan")
    traffic_predictions = relationship("TrafficPrediction", back_populates="road", cascade="all, delete-orphan")
    gnn_traffic_predictions = relationship("GNNTrafficPrediction", back_populates="road", cascade="all, delete-orphan")

# 4. Building Model
class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    building_type = Column(String(100))
    height = Column(Numeric)
    levels = Column(Integer)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 5. Hospital Model
class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    beds = Column(Integer, default=0)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 6. School Model
class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    institution_type = Column(String(100))
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 6.1. PoliceStation Model
class PoliceStation(Base):
    __tablename__ = "police_stations"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 6.2. FireStation Model
class FireStation(Base):
    __tablename__ = "fire_stations"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 7. BusStop Model
class BusStop(Base):
    __tablename__ = "bus_stops"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250))
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 8. BusRoute Model
class BusRoute(Base):
    __tablename__ = "bus_routes"

    id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String(100), nullable=False)
    operator = Column(String(100), default="CRUT")
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 9. WaterBody Model
class WaterBody(Base):
    __tablename__ = "water_bodies"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(150))
    water_type = Column(String(50))
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 10. Weather Model
class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    temperature = Column(Numeric)
    rainfall = Column(Numeric)
    humidity = Column(Numeric)
    wind_speed = Column(Numeric)
    is_forecast = Column(Boolean, default=False)
    source = Column(String(100), nullable=False)

# 11. AirQuality Model
class AirQuality(Base):
    __tablename__ = "air_quality"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    station_name = Column(String(100), nullable=False)
    pm25 = Column(Numeric)
    pm10 = Column(Numeric)
    co = Column(Numeric)
    no2 = Column(Numeric)
    so2 = Column(Numeric)
    o3 = Column(Numeric)
    aqi_value = Column(Integer)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    source = Column(String(100), nullable=False)

# 12. Traffic Model
class Traffic(Base):
    __tablename__ = "traffic"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_speed = Column(Integer, nullable=False)
    congestion_ratio = Column(Numeric)
    source = Column(String(100), nullable=False)

    road = relationship("Road", back_populates="traffic_observations")

# 13. PopulationGrid Model
class PopulationGrid(Base):
    __tablename__ = "population"

    id = Column(Integer, primary_key=True, index=True)
    population_count = Column(Integer, nullable=False)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 14. FloodEvent Model
class FloodEvent(Base):
    __tablename__ = "flood_events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(150))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    severity = Column(String(50))
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 15. SpatialGridCell Model
class SpatialGridCell(Base):
    __tablename__ = "spatial_grid_cells"

    id = Column(Integer, primary_key=True, index=True)
    cell_code = Column(String(50), unique=True, nullable=False, index=True)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    centroid = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    satellite_features = relationship("SatelliteFeature", back_populates="grid_cell", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="grid_cell", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="grid_cell", cascade="all, delete-orphan")

# 16. SatelliteFeature Model
class SatelliteFeature(Base):
    __tablename__ = "satellite_features"

    id = Column(Integer, primary_key=True, index=True)
    cell_id = Column(Integer, ForeignKey("spatial_grid_cells.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    elevation = Column(Numeric)
    slope = Column(Numeric)
    ndvi = Column(Numeric)
    ndwi = Column(Numeric)
    ndbi = Column(Numeric)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    grid_cell = relationship("SpatialGridCell", back_populates="satellite_features")

# 17. Prediction Model
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    cell_id = Column(Integer, ForeignKey("spatial_grid_cells.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction_time = Column(DateTime(timezone=True), nullable=False, index=True)
    predicted_probability = Column(Numeric, nullable=False)
    predicted_class = Column(String(50), nullable=False)
    feature_importance_shap = Column(JSON)

    grid_cell = relationship("SpatialGridCell", back_populates="predictions")

# 18. Simulation Model
class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_uuid = Column(String(36), nullable=False, index=True)  # Stores UUID as string
    scenario_name = Column(String(100), nullable=False)
    triggered_by = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    cell_id = Column(Integer, ForeignKey("spatial_grid_cells.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_class = Column(String(50), nullable=False)
    simulated_class = Column(String(50), nullable=False)
    delta_risk = Column(Numeric, nullable=False)

    grid_cell = relationship("SpatialGridCell", back_populates="simulations")


# 19. ETLJobRun Model
class ETLJobRun(Base):
    __tablename__ = "etl_job_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)      # e.g., "weather", "air_quality", "population", "dem", "sentinel2"
    dataset = Column(String(100), nullable=False)                 # e.g., "open-meteo", "openaq", "worldpop-2020", "copernicus-glo30", "sentinel2-ndvi"
    job_uuid = Column(String(36), nullable=False, unique=True, index=True)
    execution_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False)                  # e.g., "success", "failed", "partial"
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    error_message = Column(String(1000))
    duration = Column(Numeric)                                     # Duration in seconds


# 20. TrafficPrediction Model
class TrafficPrediction(Base):
    __tablename__ = "traffic_predictions"

    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_time = Column(DateTime(timezone=True), nullable=False, index=True)
    forecast_horizon_minutes = Column(Integer, nullable=False)
    predicted_speed = Column(Numeric, nullable=False)
    predicted_congestion_ratio = Column(Numeric)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_synthetic = Column(Boolean, default=True, nullable=False)
    data_provenance_status = Column(String(50), nullable=False)

    road = relationship("Road", back_populates="traffic_predictions")


# 21. AirQualityPrediction Model
class AirQualityPrediction(Base):
    __tablename__ = "air_quality_predictions"

    id = Column(Integer, primary_key=True, index=True)
    station_name = Column(String(100), nullable=False, index=True)
    pollutant = Column(String(20), nullable=False, index=True)
    forecast_issue_time = Column(DateTime(timezone=True), nullable=False, index=True)
    target_time = Column(DateTime(timezone=True), nullable=False, index=True)
    horizon_hours = Column(Integer, nullable=False, index=True)
    predicted_value = Column(Numeric, nullable=False)
    aqi_sub_index = Column(Integer)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_synthetic = Column(Boolean, default=True, nullable=False)
    data_provenance_status = Column(String(50), nullable=False)


# 22. GNNTrafficPrediction Model
class GNNTrafficPrediction(Base):
    __tablename__ = "gnn_traffic_predictions"

    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_time = Column(DateTime(timezone=True), nullable=False, index=True)
    forecast_horizon_minutes = Column(Integer, nullable=False)
    predicted_speed = Column(Numeric, nullable=False)
    predicted_congestion_ratio = Column(Numeric)
    gnn_architecture = Column(String(50), nullable=False, default="GraphSAGE")
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_synthetic = Column(Boolean, default=True, nullable=False)
    data_provenance_status = Column(String(50), nullable=False)

    road = relationship("Road", back_populates="gnn_traffic_predictions")


# 23. CityStateSnapshot Model
class CityStateSnapshot(Base):
    __tablename__ = "city_state_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    spatial_unit_type = Column(String(50), nullable=False, index=True, default="grid_cell")
    spatial_id = Column(String(100), nullable=False, index=True)
    cell_id = Column(Integer, ForeignKey("spatial_grid_cells.id", ondelete="CASCADE"), nullable=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id", ondelete="SET NULL"), nullable=True, index=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)

    state_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    target_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    forecast_horizon_minutes = Column(Integer, default=0, nullable=False, index=True)
    state_type = Column(String(20), nullable=False, default="CURRENT", index=True)  # CURRENT or FORECAST

    # High-value normalized query fields
    flood_risk_probability = Column(Numeric, nullable=True)
    flood_risk_level = Column(String(20), nullable=True)
    traffic_congestion_index = Column(Numeric, nullable=True)
    aqi_value = Column(Integer, nullable=True)
    air_quality_category = Column(String(50), nullable=True)
    population_count = Column(Integer, nullable=True)
    population_density = Column(Numeric, nullable=True)
    emergency_service_density = Column(Numeric, nullable=True)

    # Metadata & Provenance
    is_synthetic = Column(Boolean, default=False, nullable=False)
    data_provenance_status = Column(String(50), nullable=False, default="observed")
    state_schema_version = Column(String(20), nullable=False, default="1.0.0")

    # Geometry for PostGIS spatial queries
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=True)

    # Complete canonical state payload JSON
    payload = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 24. SimulationRun Model
class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(36), unique=True, nullable=False, index=True)
    scenario_type = Column(String(50), nullable=False, index=True)
    scenario_name = Column(String(150), nullable=False)
    base_state_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    simulation_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    spatial_scope_type = Column(String(50), nullable=False, default="all")
    engine_version = Column(String(20), nullable=False, default="1.0.0")
    is_synthetic = Column(Boolean, default=True, nullable=False)

    parameters = Column(JSON, nullable=False)
    impact_summary = Column(JSON, nullable=False)
    provenance = Column(JSON, nullable=False)
    transformations = Column(JSON, nullable=False)

    base_state_count = Column(Integer, default=1, nullable=False)
    simulated_state_count = Column(Integer, default=1, nullable=False)
    simulated_states_payload = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 25. OptimizationRun Model
class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(36), unique=True, nullable=False, index=True)
    scenario_id = Column(String(36), nullable=True, index=True)
    simulation_id = Column(String(36), nullable=True, index=True)
    base_state_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    optimization_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    optimization_method = Column(String(50), nullable=False, default="ortools_min_cost_flow")
    objective_function = Column(String(100), nullable=False, default="minimize_weighted_travel_cost")
    engine_version = Column(String(20), nullable=False, default="1.0.0")
    is_synthetic = Column(Boolean, default=True, nullable=False)

    constraints = Column(JSON, nullable=False)
    resource_types = Column(JSON, nullable=False)
    
    total_demand = Column(Integer, default=0, nullable=False)
    served_demand = Column(Integer, default=0, nullable=False)
    unserved_demand = Column(Integer, default=0, nullable=False)
    total_travel_cost = Column(Numeric, default=0.0, nullable=False)
    average_travel_cost = Column(Numeric, default=0.0, nullable=False)

    demand_summary = Column(JSON, nullable=False)
    resource_summary = Column(JSON, nullable=False)
    allocation_results = Column(JSON, nullable=False)
    baseline_results = Column(JSON, nullable=False)
    impact_comparison = Column(JSON, nullable=True)
    provenance = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())







