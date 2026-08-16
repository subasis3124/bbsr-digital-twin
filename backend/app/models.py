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
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 2. Ward Model
class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    ward_number = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(150))
    population_est = Column(Integer)
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)
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
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    traffic_observations = relationship("Traffic", back_populates="road", cascade="all, delete-orphan")

# 4. Building Model
class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    building_type = Column(String(100))
    height = Column(Numeric)
    levels = Column(Integer)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 5. Hospital Model
class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    beds = Column(Integer, default=0)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 6. School Model
class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250), nullable=False)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 7. BusStop Model
class BusStop(Base):
    __tablename__ = "bus_stops"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(250))
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 8. BusRoute Model
class BusRoute(Base):
    __tablename__ = "bus_routes"

    id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String(100), nullable=False)
    operator = Column(String(100), default="CRUT")
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 9. WaterBody Model
class WaterBody(Base):
    __tablename__ = "water_bodies"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(Numeric, unique=True, index=True)
    name = Column(String(150))
    water_type = Column(String(50))
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
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
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
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
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 14. FloodEvent Model
class FloodEvent(Base):
    __tablename__ = "flood_events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(150))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    severity = Column(String(50))
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 15. SpatialGridCell Model
class SpatialGridCell(Base):
    __tablename__ = "spatial_grid_cells"

    id = Column(Integer, primary_key=True, index=True)
    cell_code = Column(String(50), unique=True, nullable=False, index=True)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    centroid = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
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
