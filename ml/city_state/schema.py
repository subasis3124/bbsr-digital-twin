from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SpatialIdentity(BaseModel):
    spatial_unit_type: str = Field(default="grid_cell", description="grid_cell, road, ward")
    spatial_id: str = Field(..., description="Canonical spatial code or identifier")
    cell_id: Optional[int] = None
    cell_code: Optional[str] = None
    ward_id: Optional[int] = None
    ward_number: Optional[int] = None
    road_id: Optional[int] = None
    centroid: Optional[List[float]] = None
    bbox: Optional[List[float]] = None
    geometry: Optional[Dict[str, Any]] = None

class TemporalIdentity(BaseModel):
    state_timestamp: str = Field(..., description="ISO 8601 observation timestamp")
    target_timestamp: str = Field(..., description="ISO 8601 forecast/target timestamp")
    forecast_horizon_minutes: int = Field(default=0, ge=0)
    state_type: str = Field(default="CURRENT", description="CURRENT or FORECAST")

class MobilityState(BaseModel):
    observed_speed: Optional[float] = None
    maxspeed: Optional[int] = None
    congestion_ratio: Optional[float] = None
    forecast_speed: Optional[float] = None
    forecast_congestion_ratio: Optional[float] = None
    gnn_forecast_speed: Optional[float] = None
    gnn_forecast_congestion_ratio: Optional[float] = None
    road_accessibility: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "open-traffic"
    status: str = "AVAILABLE"

class EnvironmentalState(BaseModel):
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    co: Optional[float] = None
    no2: Optional[float] = None
    so2: Optional[float] = None
    o3: Optional[float] = None
    aqi_value: Optional[int] = None
    air_quality_category: Optional[str] = None
    temperature: Optional[float] = None
    rainfall: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    elevation: Optional[float] = None
    slope: Optional[float] = None
    ndvi: Optional[float] = None
    ndwi: Optional[float] = None
    ndbi: Optional[float] = None
    source: str = "openaq/open-meteo/sentinel"
    status: str = "AVAILABLE"

class HazardState(BaseModel):
    flood_risk_probability: Optional[float] = None
    flood_risk_level: Optional[str] = "LOW"
    severity: Optional[str] = "NORMAL"
    active_flood_event: bool = False
    source: str = "flood_risk_rf_v1"
    status: str = "AVAILABLE"

class PopulationContext(BaseModel):
    population_count: Optional[int] = None
    population_density: Optional[float] = None
    status: str = "AVAILABLE"

class InfrastructureContext(BaseModel):
    hospitals_count: int = 0
    hospital_beds: int = 0
    schools_count: int = 0
    police_stations_count: int = 0
    fire_stations_count: int = 0
    bus_stops_count: int = 0
    bus_routes_count: int = 0
    water_bodies_count: int = 0
    emergency_service_density: float = 0.0
    status: str = "AVAILABLE"

class ProvenanceMetadata(BaseModel):
    sources: List[str] = Field(default_factory=list)
    model_names: List[str] = Field(default_factory=list)
    model_versions: List[str] = Field(default_factory=list)
    is_synthetic: bool = False
    data_provenance_status: str = "observed"
    scientific_validation_warning: Optional[str] = None
    confidence_available: bool = False
    state_schema_version: str = "1.0.0"
    generated_at: str = Field(...)

class DerivedIndicators(BaseModel):
    traffic_congestion_index: Optional[float] = None
    flood_risk_level: Optional[str] = None
    air_quality_category: Optional[str] = None
    rainfall_intensity: Optional[str] = None
    emergency_service_density: Optional[float] = None
    population_density: Optional[float] = None
    road_accessibility: Optional[float] = None

class CityState(BaseModel):
    location: SpatialIdentity
    time: TemporalIdentity
    mobility: MobilityState
    environment: EnvironmentalState
    hazards: HazardState
    population: PopulationContext
    infrastructure: InfrastructureContext
    provenance: ProvenanceMetadata
    derived: DerivedIndicators
    component_statuses: Dict[str, str] = Field(default_factory=dict)
