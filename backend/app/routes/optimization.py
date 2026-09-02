from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app import models
from ml.optimization import (
    EmergencyOptimizationEngine, OptimizationRequest, OptimizationResult,
    OptimizationConstraints, EmergencyDemand, EmergencyResource
)
from ml.optimization.resources import EmergencyResourceExtractor

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


class RunOptimizationPayload(BaseModel):
    base_timestamp: Optional[str] = Field(default=None, description="ISO timestamp for baseline state")
    simulation_id: Optional[str] = Field(default=None, description="Optional simulation_id UUID to optimize under what-if scenario")
    resource_types: List[str] = Field(default_factory=lambda: ["hospital"], description="List of target resource types (hospital, police_station, fire_station)")
    demands: Optional[List[EmergencyDemand]] = Field(default=None, description="Explicit demand points (generated automatically if omitted)")
    resources: Optional[List[EmergencyResource]] = Field(default=None, description="Explicit resource locations (loaded from DB if omitted)")
    constraints: Optional[OptimizationConstraints] = Field(default=None)
    method: str = Field(default="ortools_min_cost_flow", description="Optimization method: ortools_min_cost_flow or nearest_resource")
    save: bool = Field(default=True, description="Save optimization run to database")


@router.post("/emergency", status_code=status.HTTP_201_CREATED)
def run_emergency_optimization(
    payload: RunOptimizationPayload,
    db: Session = Depends(get_db)
):
    """
    Executes emergency resource optimization to allocate emergency cases to available facilities
    under current or simulated city state conditions.
    """
    ts_base = None
    if payload.base_timestamp:
        try:
            ts_base = datetime.fromisoformat(payload.base_timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ISO format for base_timestamp."
            )

    engine = EmergencyOptimizationEngine(db=db)

    try:
        result = engine.optimize(
            base_timestamp=ts_base,
            simulation_id=payload.simulation_id,
            resource_types=payload.resource_types,
            demands=payload.demands,
            resources=payload.resources,
            constraints=payload.constraints,
            method=payload.method,
            save=payload.save
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
            detail=f"Optimization execution error: {str(err)}"
        )


@router.get("/emergency")
def list_optimization_runs(
    simulation_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Lists persisted emergency resource optimization runs.
    """
    query = db.query(models.OptimizationRun)
    if simulation_id:
        query = query.filter(models.OptimizationRun.simulation_id == simulation_id)

    total = query.count()
    runs = query.order_by(models.OptimizationRun.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "run_id": r.run_id,
                "simulation_id": r.simulation_id,
                "optimization_method": r.optimization_method,
                "objective_function": r.objective_function,
                "total_demand": r.total_demand,
                "served_demand": r.served_demand,
                "unserved_demand": r.unserved_demand,
                "total_travel_cost": float(r.total_travel_cost),
                "average_travel_cost": float(r.average_travel_cost),
                "engine_version": r.engine_version,
                "is_synthetic": r.is_synthetic,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in runs
        ]
    }


@router.get("/emergency/{run_id}")
def get_optimization_detail(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves full details of a specific emergency optimization run by run_id (UUID).
    """
    run = db.query(models.OptimizationRun).filter(models.OptimizationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run '{run_id}' not found."
        )

    return {
        "run_id": run.run_id,
        "simulation_id": run.simulation_id,
        "base_state_timestamp": run.base_state_timestamp.isoformat() if run.base_state_timestamp else None,
        "optimization_timestamp": run.optimization_timestamp.isoformat() if run.optimization_timestamp else None,
        "optimization_method": run.optimization_method,
        "objective_function": run.objective_function,
        "engine_version": run.engine_version,
        "is_synthetic": run.is_synthetic,
        "constraints": run.constraints,
        "resource_types": run.resource_types,
        "summary": {
            "total_demand": run.total_demand,
            "served_demand": run.served_demand,
            "unserved_demand": run.unserved_demand,
            "total_travel_cost": float(run.total_travel_cost),
            "average_travel_cost": float(run.average_travel_cost),
            "demand_summary": run.demand_summary,
            "resource_summary": run.resource_summary
        },
        "allocations": run.allocation_results,
        "baseline_comparison": run.baseline_results,
        "impact_comparison": run.impact_comparison,
        "provenance": run.provenance,
        "created_at": run.created_at.isoformat() if run.created_at else None
    }


@router.get("/emergency/{run_id}/allocations")
def get_optimization_allocations(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves individual demand assignment allocations for a specific run.
    """
    run = db.query(models.OptimizationRun).filter(models.OptimizationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run '{run_id}' not found."
        )

    return {
        "run_id": run.run_id,
        "allocation_count": len(run.allocation_results or []),
        "allocations": run.allocation_results
    }


@router.get("/emergency/{run_id}/impact")
def get_optimization_impact(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves impact comparisons: baseline comparison metrics and simulation allocation deltas.
    """
    run = db.query(models.OptimizationRun).filter(models.OptimizationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run '{run_id}' not found."
        )

    return {
        "run_id": run.run_id,
        "simulation_id": run.simulation_id,
        "baseline_comparison": run.baseline_results,
        "simulation_impact_delta": run.impact_comparison
    }


@router.get("/resources")
def list_available_emergency_resources(
    resource_types: Optional[List[str]] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Lists available emergency infrastructure facilities (Hospitals, Police Stations, Fire Stations) in Bhubaneswar.
    """
    types = resource_types or ["hospital", "police_station", "fire_station"]
    resources = EmergencyResourceExtractor.extract_from_db(db, resource_types=types)
    
    return {
        "total_resources": len(resources),
        "resource_types": types,
        "resources": [r.model_dump() for r in resources]
    }
