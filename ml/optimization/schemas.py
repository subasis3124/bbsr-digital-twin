from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class SpatialLocation(BaseModel):
    spatial_unit_type: str = "point"  # "point", "grid_cell", "ward", "road"
    spatial_id: str
    cell_code: Optional[str] = None
    coordinates: List[float]  # [lon, lat]


class EmergencyDemand(BaseModel):
    demand_id: str
    spatial_id: str
    coordinates: List[float]  # [lon, lat]
    timestamp: str
    demand_quantity: int = 1
    emergency_type: str = "medical"  # "medical", "fire", "police", "general"
    priority: str = "NORMAL"  # "CRITICAL", "HIGH", "NORMAL"
    priority_weight: float = 1.0  # 3.0 for CRITICAL, 1.5 for HIGH, 1.0 for NORMAL
    source: str = "population_estimate"  # "population_estimate", "simulated_surge", "scenario_input"
    is_synthetic: bool = True
    provenance: Dict[str, Any] = Field(default_factory=dict)


class EmergencyResource(BaseModel):
    resource_id: str
    resource_type: str  # "hospital", "police_station", "fire_station"
    name: str
    coordinates: List[float]  # [lon, lat]
    capacity: Optional[int] = None  # None / -1 means unknown capacity
    capacity_status: str = "known"  # "known", "unknown", "scenario_defined"
    available_capacity: int = 0
    accessibility: float = 1.0  # 0.0 to 1.0
    status: str = "AVAILABLE"  # "AVAILABLE", "DEGRADED", "INACCESSIBLE"
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class DemandAssignment(BaseModel):
    demand_id: str
    assigned_resource_id: Optional[str] = None
    resource_type: str
    allocation_quantity: int
    travel_cost: float  # travel time (minutes) or network/euclidean distance (km)
    travel_cost_unit: str = "km"
    accessibility: float
    priority: str
    assignment_status: str  # "ASSIGNED", "UNSERVED", "INACCESSIBLE"
    explanation: str


class OptimizationConstraints(BaseModel):
    capacity_constrained: bool = True
    accessibility_constrained: bool = True
    max_travel_cost: Optional[float] = None
    priority_weighting: bool = True


class OptimizationRequest(BaseModel):
    base_timestamp: Optional[str] = None
    simulation_id: Optional[str] = None
    resource_types: List[str] = Field(default_factory=lambda: ["hospital"])
    demands: Optional[List[EmergencyDemand]] = None
    resources: Optional[List[EmergencyResource]] = None
    constraints: Optional[OptimizationConstraints] = None
    method: str = "ortools_min_cost_flow"  # "ortools_min_cost_flow", "nearest_resource"
    save: bool = False


class BaselineComparison(BaseModel):
    baseline_method: str = "NEAREST_AVAILABLE_RESOURCE"
    total_travel_cost_diff: float
    avg_travel_cost_diff: float
    unserved_demand_diff: int
    improvement_percentage: float
    comparison_summary: str


class OptimizationSummary(BaseModel):
    total_demand: int
    served_demand: int
    unserved_demand: int
    total_travel_cost: float
    average_travel_cost: float
    max_travel_cost: float
    resource_utilization: Dict[str, Dict[str, Any]]
    bottlenecks: List[str]
    inaccessible_resources: List[str]
    constraint_violations: List[str]


class OptimizationResult(BaseModel):
    run_id: str
    timestamp: str
    simulation_id: Optional[str] = None
    optimization_method: str
    objective_function: str
    constraints: Dict[str, Any]
    summary: OptimizationSummary
    allocations: List[DemandAssignment]
    baseline_comparison: BaselineComparison
    allocation_delta: Optional[Dict[str, Any]] = None
    provenance: Dict[str, Any]
    engine_version: str = "1.0.0"
