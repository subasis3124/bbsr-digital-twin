from typing import Dict, Any, Callable, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.app import models
from backend.app.schemas import GeoJSONFeatureCollection
from backend.app.routes.dashboard import get_dashboard_summary as fetch_dashboard_summary
from backend.app.routes.flood_risk import get_flood_risk as fetch_flood_risk
from backend.app.routes.gnn_traffic import get_gnn_traffic_predictions as fetch_gnn_traffic
from backend.app.routes.air_quality import get_air_quality_forecasts as fetch_air_quality
from ml.simulation import WhatIfSimulationEngine
from ml.optimization import EmergencyOptimizationEngine
from ml.city_state import CityStateAggregator


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameter_schema: Dict[str, Any]
    provenance_source: str


# Parameter Schema Models for Strict Validation

class DashboardSummaryParams(BaseModel):
    pass


class FloodRiskParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    risk_level: Optional[str] = Field(default=None, description="LOW, MEDIUM, HIGH, VERY HIGH")
    ward_id: Optional[int] = Field(default=None)


class GNNTrafficParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    forecast_horizon_minutes: int = Field(default=0, ge=0, le=120)
    road_id: Optional[int] = Field(default=None)


class AirQualityParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    pollutant: Optional[str] = Field(default=None)


class InfrastructureParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    ward_id: Optional[int] = Field(default=None)


class WardQueryParams(BaseModel):
    limit: int = Field(default=100, ge=1, le=100)
    ward_number: Optional[int] = Field(default=None)


class SimulationParams(BaseModel):
    scenario_type: str = Field(..., description="heavy_rainfall, road_closure, air_pollution, emergency_demand")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    spatial_scope: Optional[Dict[str, Any]] = Field(default=None)


class SimulationResultParams(BaseModel):
    simulation_id: str = Field(...)


class OptimizationParams(BaseModel):
    resource_types: List[str] = Field(default_factory=lambda: ["hospital"])
    method: str = Field(default="ortools_min_cost_flow")
    simulation_id: Optional[str] = Field(default=None)


class OptimizationResultParams(BaseModel):
    run_id: str = Field(...)


class CityStateParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    spatial_unit_type: Optional[str] = Field(default="ward")


# Tool Execution Functions

def execute_get_dashboard_summary(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    return fetch_dashboard_summary(db=db)


def execute_get_flood_risk(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = FloodRiskParams(**params)
    query = db.query(models.Prediction, models.SpatialGridCell).join(
        models.SpatialGridCell, models.Prediction.cell_id == models.SpatialGridCell.id
    )
    if validated.risk_level:
        query = query.filter(func.upper(models.Prediction.predicted_class) == validated.risk_level.upper())
    if validated.ward_id:
        query = query.filter(models.SpatialGridCell.ward_id == validated.ward_id)

    results = query.limit(validated.limit).all()
    cells = []
    by_risk = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "VERY HIGH": 0}
    
    for pred, cell in results:
        risk_cat = (pred.predicted_class or "LOW").upper()
        if risk_cat in by_risk:
            by_risk[risk_cat] += 1
        cells.append({
            "cell_id": cell.id,
            "cell_code": cell.cell_code,
            "risk_level": pred.predicted_class,
            "probability": float(pred.predicted_probability),
            "shap_attribution": pred.feature_importance_shap or {}
        })

    is_synthetic = (db.query(models.FloodEvent).count() == 0)
    return {
        "count": len(cells),
        "risk_breakdown": by_risk,
        "cells": cells,
        "is_synthetic": is_synthetic,
        "model_name": "RandomForest_FloodRisk_v1"
    }


def execute_get_traffic_forecast(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = GNNTrafficParams(**params)
    query = db.query(models.GNNTrafficPrediction, models.Road).join(
        models.Road, models.GNNTrafficPrediction.road_id == models.Road.id
    )
    if validated.road_id:
        query = query.filter(models.GNNTrafficPrediction.road_id == validated.road_id)

    results = query.limit(validated.limit).all()
    roads = []
    congested_count = 0
    total_speed = 0.0

    for pred, road in results:
        speed = float(pred.predicted_speed or 0)
        congestion = float(pred.predicted_congestion_ratio or 0)
        total_speed += speed
        if congestion > 0.7:
            congested_count += 1
        roads.append({
            "road_id": road.id,
            "road_name": road.name or f"Road {road.id}",
            "road_type": road.road_type,
            "speed_kmh": round(speed, 1),
            "congestion_ratio": round(congestion, 2),
            "flow_vehicles_per_hr": pred.predicted_flow
        })

    avg_speed = round(total_speed / max(1, len(roads)), 1)
    return {
        "count": len(roads),
        "average_speed_kmh": avg_speed,
        "congested_count": congested_count,
        "forecast_horizon_minutes": validated.forecast_horizon_minutes,
        "roads": roads,
        "is_synthetic": True,
        "model_name": "SpatioTemporal_GNN_v1"
    }


def execute_get_air_quality(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = AirQualityParams(**params)
    query = db.query(models.AirQualityPrediction)
    if validated.pollutant:
        query = query.filter(func.upper(models.AirQualityPrediction.pollutant) == validated.pollutant.upper())
    preds = query.limit(validated.limit).all()
    records = []
    total_val = 0.0
    is_synthetic = True

    for p in preds:
        val = float(p.predicted_value or 0)
        total_val += val
        if hasattr(p, "is_synthetic") and p.is_synthetic is not None:
            is_synthetic = p.is_synthetic
        records.append({
            "station_name": p.station_name,
            "pollutant": p.pollutant,
            "predicted_value": round(val, 1),
            "aqi_sub_index": p.aqi_sub_index,
            "horizon_hours": p.horizon_hours
        })

    avg_val = round(total_val / max(1, len(records)), 1)
    return {
        "count": len(records),
        "average_pollutant_value": avg_val,
        "stations": records,
        "is_synthetic": is_synthetic,
        "model_name": "XGBoost_AirQuality_v1"
    }


def execute_get_hospitals(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    query = db.query(models.Hospital)
    if validated.ward_id:
        query = query.filter(models.Hospital.ward_id == validated.ward_id)
    records = query.limit(validated.limit).all()
    
    return {
        "count": len(records),
        "hospitals": [
            {
                "id": r.id,
                "name": r.name,
                "hospital_type": r.hospital_type,
                "bed_capacity": r.bed_capacity if r.bed_capacity else "Capacity unavailable",
                "ward_id": r.ward_id,
                "phone": r.phone
            }
            for r in records
        ]
    }


def execute_get_police_stations(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.PoliceStation).limit(validated.limit).all()
    return {
        "count": len(records),
        "police_stations": [
            {
                "id": r.id,
                "name": r.name,
                "ward_id": r.ward_id
            }
            for r in records
        ]
    }


def execute_get_fire_stations(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.FireStation).limit(validated.limit).all()
    return {
        "count": len(records),
        "fire_stations": [
            {
                "id": r.id,
                "name": r.name,
                "ward_id": r.ward_id
            }
            for r in records
        ]
    }


def execute_get_roads(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.Road).limit(validated.limit).all()
    return {
        "count": len(records),
        "roads": [
            {
                "id": r.id,
                "name": r.name or f"Road {r.id}",
                "road_type": r.road_type,
                "speed_limit_kmh": r.speed_limit
            }
            for r in records
        ]
    }


def execute_get_wards(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = WardQueryParams(**params)
    query = db.query(models.Ward)
    if validated.ward_number:
        query = query.filter(models.Ward.ward_number == validated.ward_number)
    records = query.limit(validated.limit).all()
    return {
        "count": len(records),
        "wards": [
            {
                "id": r.id,
                "ward_number": r.ward_number,
                "name": r.name,
                "zone_name": r.zone_name,
                "population": r.population
            }
            for r in records
        ]
    }


def execute_get_bus_routes(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.BusRoute).limit(validated.limit).all()
    return {
        "count": len(records),
        "bus_routes": [{"id": r.id, "route_name": r.route_name, "route_number": r.route_number} for r in records]
    }


def execute_get_bus_stops(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.BusStop).limit(validated.limit).all()
    return {
        "count": len(records),
        "bus_stops": [{"id": r.id, "stop_name": r.name, "ward_id": r.ward_id} for r in records]
    }


def execute_get_water_bodies(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = InfrastructureParams(**params)
    records = db.query(models.WaterBody).limit(validated.limit).all()
    return {
        "count": len(records),
        "water_bodies": [{"id": r.id, "name": r.name, "water_type": r.water_type} for r in records]
    }


def execute_run_simulation(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = SimulationParams(**params)
    engine = WhatIfSimulationEngine(db=db)
    result = engine.run_simulation(
        scenario_type=validated.scenario_type,
        parameters=validated.parameters,
        spatial_scope=validated.spatial_scope,
        save=True
    )
    return result.model_dump()


def execute_get_simulation_result(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = SimulationResultParams(**params)
    run = db.query(models.SimulationRun).filter(models.SimulationRun.simulation_id == validated.simulation_id).first()
    if not run:
        return {"error": f"Simulation '{validated.simulation_id}' not found."}
    return {
        "simulation_id": run.simulation_id,
        "scenario_type": run.scenario_type,
        "scenario_name": run.scenario_name,
        "impact_summary": run.impact_summary,
        "provenance": run.provenance,
        "is_synthetic": run.is_synthetic
    }


def execute_run_emergency_optimization(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = OptimizationParams(**params)
    engine = EmergencyOptimizationEngine(db=db)
    result = engine.optimize(
        resource_types=validated.resource_types,
        method=validated.method,
        simulation_id=validated.simulation_id,
        save=True
    )
    return result.model_dump()


def execute_get_optimization_result(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = OptimizationResultParams(**params)
    run = db.query(models.OptimizationRun).filter(models.OptimizationRun.run_id == validated.run_id).first()
    if not run:
        return {"error": f"Optimization run '{validated.run_id}' not found."}
    return {
        "run_id": run.run_id,
        "optimization_method": run.optimization_method,
        "total_demand": run.total_demand,
        "served_demand": run.served_demand,
        "unserved_demand": run.unserved_demand,
        "total_travel_cost": float(run.total_travel_cost),
        "average_travel_cost": float(run.average_travel_cost),
        "baseline_comparison": run.baseline_results,
        "is_synthetic": run.is_synthetic
    }


def execute_get_city_state(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    validated = CityStateParams(**params)
    aggregator = CityStateAggregator(db=db)
    metadata = aggregator.get_state_metadata()
    states = aggregator.aggregate_city_state(limit=validated.limit)
    return {
        "snapshot": metadata.model_dump(),
        "total_units": len(states),
        "sample_units": [s.model_dump() for s in states[:10]]
    }


# CONTROLLED TOOL REGISTRY

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_dashboard_summary": {
        "definition": ToolDefinition(
            name="get_dashboard_summary",
            description="Fetch top-level aggregated KPI metrics and counts across all urban infrastructure and model outputs.",
            parameter_schema={},
            provenance_source="Dashboard Summary API"
        ),
        "schema_class": DashboardSummaryParams,
        "executor": execute_get_dashboard_summary
    },
    "get_city_state": {
        "definition": ToolDefinition(
            name="get_city_state",
            description="Retrieve aggregated unified urban state representing multi-domain city status.",
            parameter_schema={"limit": "int", "spatial_unit_type": "str"},
            provenance_source="Unified City State Engine"
        ),
        "schema_class": CityStateParams,
        "executor": execute_get_city_state
    },
    "get_flood_risk": {
        "definition": ToolDefinition(
            name="get_flood_risk",
            description="Retrieve flood risk model predictions and cell probability classifications.",
            parameter_schema={"limit": "int", "risk_level": "str (LOW, MEDIUM, HIGH, VERY HIGH)", "ward_id": "int"},
            provenance_source="Flood Risk ML Engine (RandomForest v1)"
        ),
        "schema_class": FloodRiskParams,
        "executor": execute_get_flood_risk
    },
    "get_traffic_forecast": {
        "definition": ToolDefinition(
            name="get_traffic_forecast",
            description="Retrieve forecasted traffic speeds and congestion levels for road network segments.",
            parameter_schema={"limit": "int", "forecast_horizon_minutes": "int", "road_id": "int"},
            provenance_source="Traffic Prediction Engine"
        ),
        "schema_class": GNNTrafficParams,
        "executor": execute_get_traffic_forecast
    },
    "get_gnn_traffic": {
        "definition": ToolDefinition(
            name="get_gnn_traffic",
            description="Retrieve Spatio-Temporal Graph Neural Network traffic forecasts.",
            parameter_schema={"limit": "int", "forecast_horizon_minutes": "int", "road_id": "int"},
            provenance_source="GNN Traffic Engine (ST-GNN v1)"
        ),
        "schema_class": GNNTrafficParams,
        "executor": execute_get_traffic_forecast
    },
    "get_air_quality": {
        "definition": ToolDefinition(
            name="get_air_quality",
            description="Retrieve ambient air quality forecasts and AQI station pollutant readings.",
            parameter_schema={"limit": "int", "pollutant": "str"},
            provenance_source="Air Quality ML Engine (XGBoost v1)"
        ),
        "schema_class": AirQualityParams,
        "executor": execute_get_air_quality
    },
    "get_hospitals": {
        "definition": ToolDefinition(
            name="get_hospitals",
            description="Retrieve hospital spatial locations, types, ward assignments, and bed capacity records.",
            parameter_schema={"limit": "int", "ward_id": "int"},
            provenance_source="Bhubaneswar Healthcare GIS Registry"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_hospitals
    },
    "get_police_stations": {
        "definition": ToolDefinition(
            name="get_police_stations",
            description="Retrieve police station locations and spatial metadata.",
            parameter_schema={"limit": "int", "ward_id": "int"},
            provenance_source="Bhubaneswar Police Station GIS Layer"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_police_stations
    },
    "get_fire_stations": {
        "definition": ToolDefinition(
            name="get_fire_stations",
            description="Retrieve fire station emergency response facility locations.",
            parameter_schema={"limit": "int", "ward_id": "int"},
            provenance_source="Bhubaneswar Fire Station GIS Layer"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_fire_stations
    },
    "get_roads": {
        "definition": ToolDefinition(
            name="get_roads",
            description="Retrieve road network segment geometry, classification, and speed limit metadata.",
            parameter_schema={"limit": "int", "ward_id": "int"},
            provenance_source="Bhubaneswar Road Network GIS"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_roads
    },
    "get_wards": {
        "definition": ToolDefinition(
            name="get_wards",
            description="Retrieve municipal ward boundaries, numbers, names, and population figures.",
            parameter_schema={"limit": "int", "ward_number": "int"},
            provenance_source="BMC Ward Boundary GIS Layer"
        ),
        "schema_class": WardQueryParams,
        "executor": execute_get_wards
    },
    "get_bus_routes": {
        "definition": ToolDefinition(
            name="get_bus_routes",
            description="Retrieve transit bus route networks.",
            parameter_schema={"limit": "int"},
            provenance_source="CRUT Bus Route GIS"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_bus_routes
    },
    "get_bus_stops": {
        "definition": ToolDefinition(
            name="get_bus_stops",
            description="Retrieve transit bus stop locations.",
            parameter_schema={"limit": "int"},
            provenance_source="CRUT Bus Stop GIS"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_bus_stops
    },
    "get_water_bodies": {
        "definition": ToolDefinition(
            name="get_water_bodies",
            description="Retrieve natural and urban water bodies, lakes, and drainage channels.",
            parameter_schema={"limit": "int"},
            provenance_source="Bhubaneswar Hydrographic GIS Layer"
        ),
        "schema_class": InfrastructureParams,
        "executor": execute_get_water_bodies
    },
    "run_simulation": {
        "definition": ToolDefinition(
            name="run_simulation",
            description="Execute counterfactual What-If simulation (heavy_rainfall, road_closure, air_pollution, emergency_demand).",
            parameter_schema={"scenario_type": "str", "parameters": "dict", "spatial_scope": "dict"},
            provenance_source="What-If Simulation Engine"
        ),
        "schema_class": SimulationParams,
        "executor": execute_run_simulation
    },
    "get_simulation_result": {
        "definition": ToolDefinition(
            name="get_simulation_result",
            description="Retrieve impact analysis and parameters of a previous simulation run by UUID.",
            parameter_schema={"simulation_id": "str"},
            provenance_source="What-If Simulation Engine"
        ),
        "schema_class": SimulationResultParams,
        "executor": execute_get_simulation_result
    },
    "run_emergency_optimization": {
        "definition": ToolDefinition(
            name="run_emergency_optimization",
            description="Execute capacitated emergency resource allocation optimization.",
            parameter_schema={"resource_types": "list[str]", "method": "str", "simulation_id": "str"},
            provenance_source="Emergency Resource Optimization Engine (OR-Tools)"
        ),
        "schema_class": OptimizationParams,
        "executor": execute_run_emergency_optimization
    },
    "get_optimization_result": {
        "definition": ToolDefinition(
            name="get_optimization_result",
            description="Retrieve emergency allocation results, baseline comparison, and travel cost metrics by run UUID.",
            parameter_schema={"run_id": "str"},
            provenance_source="Emergency Resource Optimization Engine"
        ),
        "schema_class": OptimizationResultParams,
        "executor": execute_get_optimization_result
    }
}


def get_registered_tool_names() -> List[str]:
    return list(TOOL_REGISTRY.keys())


def execute_tool(tool_name: str, parameters: Dict[str, Any], db: Session) -> Dict[str, Any]:
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{tool_name}' is not registered in the controlled tool registry.")

    tool_meta = TOOL_REGISTRY[tool_name]
    schema_cls = tool_meta["schema_class"]
    executor = tool_meta["executor"]

    # Validate parameters using Pydantic schema
    try:
        validated_pydantic = schema_cls(**parameters)
        clean_params = validated_pydantic.model_dump()
    except ValidationError as err:
        raise ValueError(f"Invalid parameters for tool '{tool_name}': {str(err)}")

    return executor(db=db, params=clean_params)
