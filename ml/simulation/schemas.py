from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

# ----------------------------------------------------
# 1. Spatial Scope Abstraction
# ----------------------------------------------------
class SpatialScope(BaseModel):
    scope_type: str = Field(default="all", description="all, bbox, ward, road, grid_cell")
    min_lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    min_lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    max_lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    max_lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    ward_ids: List[int] = Field(default_factory=list)
    road_ids: List[int] = Field(default_factory=list)
    cell_codes: List[str] = Field(default_factory=list)

    @field_validator("max_lon")
    @classmethod
    def validate_bbox_lon(cls, v, info):
        if v is not None and info.data.get("min_lon") is not None:
            if v < info.data["min_lon"]:
                raise ValueError("max_lon must be greater than or equal to min_lon")
        return v

    @field_validator("max_lat")
    @classmethod
    def validate_bbox_lat(cls, v, info):
        if v is not None and info.data.get("min_lat") is not None:
            if v < info.data["min_lat"]:
                raise ValueError("max_lat must be greater than or equal to min_lat")
        return v


# ----------------------------------------------------
# 2. Scenario Parameter Schemas
# ----------------------------------------------------
class HeavyRainfallParams(BaseModel):
    rainfall_multiplier: float = Field(default=1.0, gt=0.0, le=20.0, description="Multiplier for baseline rainfall")
    rainfall_delta_mm: float = Field(default=0.0, ge=0.0, le=500.0, description="Additive rainfall delta in mm")
    duration_hours: float = Field(default=1.0, gt=0.0, le=168.0, description="Event duration in hours")
    spatial_scope: SpatialScope = Field(default_factory=SpatialScope)

class RoadClosureParams(BaseModel):
    closed_road_ids: List[int] = Field(..., min_length=1, description="List of road IDs to close")
    closure_duration_hours: float = Field(default=2.0, gt=0.0, le=168.0, description="Closure duration")
    rerouting_capacity_factor: float = Field(default=0.5, ge=0.0, le=1.0, description="Detour capacity absorption factor")
    spatial_scope: SpatialScope = Field(default_factory=SpatialScope)

class AirPollutionParams(BaseModel):
    pollutant: str = Field(default="pm25", description="pm25, pm10, no2, co, so2, o3")
    multiplier: float = Field(default=1.0, gt=0.0, le=20.0, description="Pollutant multiplier")
    delta: float = Field(default=0.0, ge=0.0, le=1000.0, description="Pollutant additive delta")
    spatial_scope: SpatialScope = Field(default_factory=SpatialScope)

    @field_validator("pollutant")
    @classmethod
    def validate_pollutant_type(cls, v):
        allowed = {"pm25", "pm10", "no2", "co", "so2", "o3"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid pollutant '{v}'. Allowed values: {sorted(list(allowed))}")
        return v.lower()

class EmergencyDemandParams(BaseModel):
    hospital_demand_multiplier: float = Field(default=1.5, gt=0.0, le=10.0, description="Emergency hospital surge multiplier")
    incident_count_surge: int = Field(default=5, ge=0, description="Additional emergency incidents count")
    affected_population_factor: float = Field(default=1.2, gt=0.0, description="Population impact scaling factor")
    spatial_scope: SpatialScope = Field(default_factory=SpatialScope)


# ----------------------------------------------------
# 3. Scenario & Transformation Metadata
# ----------------------------------------------------
class SimulationScenario(BaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_type: str = Field(..., description="heavy_rainfall, road_closure, air_pollution, emergency_demand")
    scenario_name: str = Field(...)
    base_state_timestamp: str = Field(..., description="ISO timestamp of baseline city state")
    simulation_timestamp: str = Field(..., description="ISO timestamp of target simulated state")
    spatial_scope: SpatialScope = Field(default_factory=SpatialScope)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    engine_version: str = "1.0.0"

class TransformationStep(BaseModel):
    step_number: int = Field(...)
    name: str = Field(...)
    layer_affected: str = Field(..., description="environment, hazards, mobility, population, infrastructure, derived")
    input_variables: Dict[str, Any] = Field(default_factory=dict)
    output_variables: Dict[str, Any] = Field(default_factory=dict)
    method: str = Field(default="heuristic_simulation", description="heuristic_simulation, GNN_propagation, linear_perturbation")
    description: str = Field(...)


# ----------------------------------------------------
# 4. Impact Summary & Delta Models
# ----------------------------------------------------
class MetricDelta(BaseModel):
    metric_name: str = Field(...)
    base_value: Optional[float] = None
    simulated_value: Optional[float] = None
    delta_absolute: Optional[float] = None
    delta_percentage: Optional[float] = None
    category: str = Field(default="DERIVED", description="DIRECTLY_SIMULATED, DERIVED, UNCHANGED, UNAVAILABLE")
    unit: Optional[str] = None

class ImpactSummary(BaseModel):
    affected_spatial_units_count: int = Field(default=0)
    total_affected_population: int = Field(default=0)
    affected_hospitals_count: int = Field(default=0)
    affected_schools_count: int = Field(default=0)
    overall_severity: str = Field(default="MODERATE", description="LOW, MODERATE, HIGH, CRITICAL")
    metrics: Dict[str, MetricDelta] = Field(default_factory=dict)
    spatial_unit_deltas: List[Dict[str, Any]] = Field(default_factory=list)


# ----------------------------------------------------
# 5. Full Simulation Result Payload
# ----------------------------------------------------
class SimulationResult(BaseModel):
    scenario: SimulationScenario
    base_states: List[Dict[str, Any]] = Field(default_factory=list)
    simulated_states: List[Dict[str, Any]] = Field(default_factory=list)
    impact_summary: ImpactSummary
    transformations: List[TransformationStep] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
