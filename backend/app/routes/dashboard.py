from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app import models

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

SCIENTIFIC_WARNING = (
    "WARNING: Dashboard KPI values are aggregated from underlying city-state snapshot models "
    "and synthetic fallbacks. Predictions and optimization outputs are decision-support estimates."
)

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated high-level city stats, infrastructure counts, model summaries,
    and system status for the Command Center KPI panel.
    """
    # 1. Spatial Infrastructure counts
    ward_count = db.query(models.Ward).count()
    grid_count = db.query(models.SpatialGridCell).count()
    road_count = db.query(models.Road).count()
    hospital_count = db.query(models.Hospital).count()
    police_count = db.query(models.PoliceStation).count()
    fire_count = db.query(models.FireStation).count()
    school_count = db.query(models.School).count()
    bus_stop_count = db.query(models.BusStop).count()
    bus_route_count = db.query(models.BusRoute).count()
    water_body_count = db.query(models.WaterBody).count()

    # 2. Flood Risk summary
    flood_preds = db.query(models.Prediction).all()
    flood_by_cat = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "VERY HIGH": 0}
    for fp in flood_preds:
        cat = (fp.predicted_class or "LOW").upper()
        if cat in flood_by_cat:
            flood_by_cat[cat] += 1
        else:
            flood_by_cat[cat] = 1

    # 3. Traffic summary
    gnn_preds = db.query(models.GNNTrafficPrediction).all()
    avg_speed = 0.0
    congested_count = 0
    if gnn_preds:
        total_speed = sum(float(p.predicted_speed or 0) for p in gnn_preds)
        avg_speed = round(total_speed / len(gnn_preds), 1)
        congested_count = sum(1 for p in gnn_preds if (p.predicted_congestion_ratio or 0) > 0.7)

    # 4. Air Quality summary
    aq_preds = db.query(models.AirQualityPrediction).all()
    avg_aqi_val = 0.0
    if aq_preds:
        avg_aqi_val = round(sum(float(p.predicted_value or 0) for p in aq_preds) / len(aq_preds), 1)

    # 5. Simulation & Optimization runs summary
    sim_count = db.query(models.SimulationRun).count()
    opt_count = db.query(models.OptimizationRun).count()
    latest_sim = db.query(models.SimulationRun).order_by(models.SimulationRun.created_at.desc()).first()
    latest_opt = db.query(models.OptimizationRun).order_by(models.OptimizationRun.created_at.desc()).first()

    return {
        "engine_name": "Bhubaneswar Digital Twin Command Center",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_status": "OPERATIONAL",
        "provenance_status": "synthetic_fallback",
        "is_synthetic": True,
        "scientific_validation_warning": SCIENTIFIC_WARNING,
        "infrastructure": {
            "wards": ward_count,
            "grid_cells": grid_count,
            "roads": road_count,
            "hospitals": hospital_count,
            "police_stations": police_count,
            "fire_stations": fire_count,
            "schools": school_count,
            "bus_stops": bus_stop_count,
            "bus_routes": bus_route_count,
            "water_bodies": water_body_count
        },
        "flood_risk": {
            "total_evaluated_cells": len(flood_preds),
            "by_category": flood_by_cat,
            "high_risk_cells_count": flood_by_cat.get("HIGH", 0) + flood_by_cat.get("VERY HIGH", 0)
        },
        "traffic": {
            "monitored_segments": len(gnn_preds),
            "average_speed_kmh": avg_speed,
            "congested_segments_count": congested_count
        },
        "air_quality": {
            "forecast_count": len(aq_preds),
            "average_pollutant_value": avg_aqi_val
        },
        "simulations": {
            "total_runs": sim_count,
            "latest_run_id": latest_sim.simulation_id if latest_sim else None,
            "latest_scenario": latest_sim.scenario_type if latest_sim else None
        },
        "optimization": {
            "total_runs": opt_count,
            "latest_run_id": latest_opt.run_id if latest_opt else None,
            "latest_method": latest_opt.optimization_method if latest_opt else None
        }
    }
