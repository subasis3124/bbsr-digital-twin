from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app import models
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature
from ml.simulation import WhatIfSimulationEngine, HEURISTIC_WARNING
from ml.city_state import CityStateAggregator

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])

class CreateSimulationRequest(BaseModel):
    scenario_type: str = Field(..., description="heavy_rainfall, road_closure, air_pollution, emergency_demand")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    base_timestamp: Optional[str] = Field(default=None, description="ISO format baseline timestamp")
    simulation_timestamp: Optional[str] = Field(default=None, description="ISO format target simulation timestamp")
    spatial_scope: Optional[Dict[str, Any]] = Field(default=None)
    save: bool = Field(default=True, description="Save simulation run record to database")

@router.get("/scenarios/types")
def list_scenario_types():
    """
    Lists all supported scenario types, parameter definitions, and default options.
    """
    return {
        "engine_version": "1.0.0",
        "scientific_validation_warning": HEURISTIC_WARNING,
        "scenarios": [
            {
                "type": "heavy_rainfall",
                "name": "Heavy Rainfall Simulation Scenario",
                "description": "Simulates rainfall perturbation and propagates through flood risk, road accessibility, and traffic speed.",
                "parameter_schema": {
                    "rainfall_multiplier": {"type": "float", "default": 1.0, "min": 0.01, "max": 20.0},
                    "rainfall_delta_mm": {"type": "float", "default": 0.0, "min": 0.0, "max": 500.0},
                    "duration_hours": {"type": "float", "default": 1.0, "min": 0.1, "max": 168.0}
                }
            },
            {
                "type": "road_closure",
                "name": "Road Closure Simulation Scenario",
                "description": "Simulates road segment closures and estimates network accessibility and detour traffic congestion impact.",
                "parameter_schema": {
                    "closed_road_ids": {"type": "list[int]", "required": True},
                    "closure_duration_hours": {"type": "float", "default": 2.0, "min": 0.1, "max": 168.0},
                    "rerouting_capacity_factor": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0}
                }
            },
            {
                "type": "air_pollution",
                "name": "Air Pollution Event Scenario",
                "description": "Simulates atmospheric pollutant surges and recalculates AQI index categories.",
                "parameter_schema": {
                    "pollutant": {"type": "string", "default": "pm25", "allowed": ["pm25", "pm10", "no2", "co", "so2", "o3"]},
                    "multiplier": {"type": "float", "default": 1.0, "min": 0.01, "max": 20.0},
                    "delta": {"type": "float", "default": 0.0, "min": 0.0, "max": 1000.0}
                }
            },
            {
                "type": "emergency_demand",
                "name": "Emergency Demand Surge Scenario",
                "description": "Simulates hospital demand surge and emergency service density stress for resource optimization.",
                "parameter_schema": {
                    "hospital_demand_multiplier": {"type": "float", "default": 1.5, "min": 0.01, "max": 10.0},
                    "incident_count_surge": {"type": "int", "default": 5, "min": 0}
                }
            }
        ]
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_simulation(
    req: CreateSimulationRequest,
    db: Session = Depends(get_db)
):
    """
    Executes a What-If Simulation scenario on the base city state and produces a simulated city state + impact metrics.
    """
    ts_base = None
    if req.base_timestamp:
        try:
            ts_base = datetime.fromisoformat(req.base_timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ISO format for base_timestamp."
            )

    ts_sim = None
    if req.simulation_timestamp:
        try:
            ts_sim = datetime.fromisoformat(req.simulation_timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ISO format for simulation_timestamp."
            )

    engine = WhatIfSimulationEngine(db=db)

    try:
        result = engine.run_simulation(
            scenario_type=req.scenario_type,
            parameters=req.parameters,
            base_timestamp=ts_base,
            simulation_timestamp=ts_sim,
            spatial_scope=req.spatial_scope,
            save=req.save
        )
        return result.model_dump()
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation execution error: {str(err)}"
        )

@router.get("")
def list_simulations(
    scenario_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Lists persisted simulation runs.
    """
    query = db.query(models.SimulationRun)
    if scenario_type:
        query = query.filter(models.SimulationRun.scenario_type == scenario_type)

    total = query.count()
    runs = query.order_by(models.SimulationRun.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "simulation_id": r.simulation_id,
                "scenario_type": r.scenario_type,
                "scenario_name": r.scenario_name,
                "base_state_timestamp": r.base_state_timestamp.isoformat(),
                "simulation_timestamp": r.simulation_timestamp.isoformat(),
                "engine_version": r.engine_version,
                "is_synthetic": r.is_synthetic,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in runs
        ]
    }

@router.get("/{simulation_id}")
def get_simulation_detail(
    simulation_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full details of a specific simulation run by simulation_id (UUID).
    """
    run = db.query(models.SimulationRun).filter(models.SimulationRun.simulation_id == simulation_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{simulation_id}' not found."
        )

    return {
        "simulation_id": run.simulation_id,
        "scenario_type": run.scenario_type,
        "scenario_name": run.scenario_name,
        "base_state_timestamp": run.base_state_timestamp.isoformat(),
        "simulation_timestamp": run.simulation_timestamp.isoformat(),
        "engine_version": run.engine_version,
        "is_synthetic": run.is_synthetic,
        "parameters": run.parameters,
        "impact_summary": run.impact_summary,
        "provenance": run.provenance,
        "transformations": run.transformations,
        "base_state_count": run.base_state_count,
        "simulated_state_count": run.simulated_state_count,
        "created_at": run.created_at.isoformat() if run.created_at else None
    }

@router.get("/{simulation_id}/impact")
def get_simulation_impact(
    simulation_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the structured impact analysis metrics and spatial deltas for a simulation run.
    """
    run = db.query(models.SimulationRun).filter(models.SimulationRun.simulation_id == simulation_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{simulation_id}' not found."
        )

    return {
        "simulation_id": run.simulation_id,
        "scenario_type": run.scenario_type,
        "impact_summary": run.impact_summary
    }

@router.get("/{simulation_id}/state", response_model=GeoJSONFeatureCollection)
def get_simulated_state_geojson(
    simulation_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the simulated city states as a GeoJSON FeatureCollection.
    """
    run = db.query(models.SimulationRun).filter(models.SimulationRun.simulation_id == simulation_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{simulation_id}' not found."
        )

    sim_states = run.simulated_states_payload or []
    features = []

    for s_dict in sim_states:
        geom = None
        if "location" in s_dict and "geometry" in s_dict["location"]:
            geom = s_dict["location"]["geometry"]

        if not geom:
            geom = {"type": "Point", "coordinates": [85.83, 20.27]}

        features.append(GeoJSONFeature(
            type="Feature",
            geometry=geom,
            properties=s_dict
        ))

    return GeoJSONFeatureCollection(features=features)
