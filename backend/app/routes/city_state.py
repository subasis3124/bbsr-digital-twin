from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects, ST_MakeEnvelope
import shapely.geometry
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app import models
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature
from ml.city_state import CityStateAggregator, CityStateValidator, DataSourceRegistry

router = APIRouter(prefix="/api/v1/city-state", tags=["city_state"])

SCIENTIFIC_WARNING = (
    "WARNING: City state data layer contains components generated from synthetic validation baselines "
    "or mock fallbacks because real-time sensor streams are partially uncalibrated."
)

@router.get("/metadata")
def get_city_state_metadata(db: Session = Depends(get_db)):
    """
    Returns high-level metadata, coverage stats, active schema version, and synthetic data warnings
    for the Unified City State Engine.
    """
    total_snapshots = db.query(models.CityStateSnapshot).count()
    grid_cells_cnt = db.query(models.SpatialGridCell).count()
    wards_cnt = db.query(models.Ward).count()
    latest_snapshot = db.query(models.CityStateSnapshot).order_by(models.CityStateSnapshot.created_at.desc()).first()

    return {
        "engine_name": "Unified City State Engine",
        "state_schema_version": "1.0.0",
        "spatial_reference": "EPSG:4326",
        "canonical_spatial_units": ["grid_cell", "road", "ward"],
        "active_grid_cells_count": grid_cells_cnt,
        "active_wards_count": wards_cnt,
        "total_persisted_snapshots": total_snapshots,
        "latest_snapshot_created_at": latest_snapshot.created_at.isoformat() if latest_snapshot else None,
        "data_sources": list(DataSourceRegistry.REGISTRY.keys()),
        "is_synthetic": True,
        "data_provenance_status": "synthetic_fallback",
        "scientific_validation_warning": SCIENTIFIC_WARNING
    }

@router.get("", response_model=GeoJSONFeatureCollection)
def get_city_states(
    spatial_unit_type: str = Query(default="grid_cell", description="grid_cell, ward, road"),
    state_type: Optional[str] = Query(default=None, description="CURRENT or FORECAST"),
    forecast_horizon_minutes: Optional[int] = Query(default=None),
    cell_code: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Fetches Unified City State observations/forecasts as a GeoJSON FeatureCollection.
    Supports bounding box viewport filtering, spatial unit types, forecast horizon, and pagination.
    """
    # 1. Query persisted snapshots if present
    query = db.query(models.CityStateSnapshot)

    if spatial_unit_type:
        query = query.filter(models.CityStateSnapshot.spatial_unit_type == spatial_unit_type)
    if state_type:
        query = query.filter(models.CityStateSnapshot.state_type == state_type)
    if forecast_horizon_minutes is not None:
        query = query.filter(models.CityStateSnapshot.forecast_horizon_minutes == forecast_horizon_minutes)
    if cell_code:
        query = query.filter(models.CityStateSnapshot.spatial_id == cell_code)
    if ward_id is not None:
        query = query.filter(models.CityStateSnapshot.ward_id == ward_id)

    # BBox viewport filter
    bbox_params = [min_lon, min_lat, max_lon, max_lat]
    if any(p is not None for p in bbox_params):
        if not all(p is not None for p in bbox_params):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All bounding box parameters (min_lon, min_lat, max_lon, max_lat) must be specified."
            )
        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bounding box corners: min coordinates must be smaller than max coordinates."
            )
        envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = query.filter(ST_Intersects(models.CityStateSnapshot.geom, envelope))

    snapshots = query.offset(offset).limit(limit).all()

    # Dynamic fallback aggregation if no snapshots found in DB
    if not snapshots and spatial_unit_type == "grid_cell":
        aggregator = CityStateAggregator(db)
        grid_cells_query = db.query(models.SpatialGridCell)
        if cell_code:
            grid_cells_query = grid_cells_query.filter(models.SpatialGridCell.cell_code == cell_code)
        grid_cells = grid_cells_query.offset(offset).limit(limit).all()

        features = []
        for cell in grid_cells:
            c_state = aggregator.aggregate_grid_cell(
                cell,
                forecast_horizon_minutes=forecast_horizon_minutes or 0
            )
            features.append(GeoJSONFeature(
                type="Feature",
                geometry=c_state.location.geometry or {"type": "Point", "coordinates": [85.83, 20.27]},
                properties=c_state.model_dump()
            ))
        return GeoJSONFeatureCollection(features=features)

    features = []
    for snap in snapshots:
        payload = snap.payload or {}
        geom_geojson = None
        if snap.geom is not None:
            shape = to_shape(snap.geom)
            geom_geojson = shapely.geometry.mapping(shape)
        elif "location" in payload and "geometry" in payload["location"]:
            geom_geojson = payload["location"]["geometry"]

        if not geom_geojson:
            geom_geojson = {"type": "Point", "coordinates": [85.83, 20.27]}

        features.append(GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties=payload
        ))

    return GeoJSONFeatureCollection(features=features)

@router.get("/{spatial_id}", response_model=GeoJSONFeature)
def get_city_state_by_id(
    spatial_id: str,
    forecast_horizon_minutes: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest unified city state representation for a specific spatial ID (cell_code, road_id, ward_number).
    """
    # 1. Search database snapshot
    snap = db.query(models.CityStateSnapshot).filter(
        models.CityStateSnapshot.spatial_id == spatial_id,
        models.CityStateSnapshot.forecast_horizon_minutes == forecast_horizon_minutes
    ).order_by(models.CityStateSnapshot.created_at.desc()).first()

    if snap:
        payload = snap.payload or {}
        geom_geojson = None
        if snap.geom is not None:
            shape = to_shape(snap.geom)
            geom_geojson = shapely.geometry.mapping(shape)
        elif "location" in payload and "geometry" in payload["location"]:
            geom_geojson = payload["location"]["geometry"]

        if not geom_geojson:
            geom_geojson = {"type": "Point", "coordinates": [85.83, 20.27]}

        return GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties=payload
        )

    # 2. Try dynamic aggregation fallback for grid cell
    grid_cell = db.query(models.SpatialGridCell).filter(models.SpatialGridCell.cell_code == spatial_id).first()
    if grid_cell:
        aggregator = CityStateAggregator(db)
        c_state = aggregator.aggregate_grid_cell(grid_cell, forecast_horizon_minutes=forecast_horizon_minutes)
        return GeoJSONFeature(
            type="Feature",
            geometry=c_state.location.geometry or {"type": "Point", "coordinates": [85.83, 20.27]},
            properties=c_state.model_dump()
        )

    # 3. Try ward fallback
    try:
        ward_num = int(spatial_id)
        ward = db.query(models.Ward).filter(models.Ward.ward_number == ward_num).first()
        if ward:
            aggregator = CityStateAggregator(db)
            c_state = aggregator.aggregate_ward(ward, forecast_horizon_minutes=forecast_horizon_minutes)
            return GeoJSONFeature(
                type="Feature",
                geometry=c_state.location.geometry or {"type": "Point", "coordinates": [85.83, 20.27]},
                properties=c_state.model_dump()
            )
    except ValueError:
        pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"City state for Spatial ID '{spatial_id}' not found."
    )

@router.post("/generate")
def generate_city_state_snapshots(
    forecast_horizon_minutes: int = Query(default=0, ge=0),
    spatial_unit_type: str = Query(default="grid_cell"),
    limit: int = Query(default=50, ge=1, le=500),
    save: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """
    Triggers generation and validation of City State records across spatial units.
    Optionally saves records to the city_state_snapshots table.
    """
    aggregator = CityStateAggregator(db)
    generated_count = 0
    validation_failures = 0
    records = []

    if spatial_unit_type == "grid_cell":
        grid_cells = db.query(models.SpatialGridCell).limit(limit).all()
        for cell in grid_cells:
            c_state = aggregator.aggregate_grid_cell(cell, forecast_horizon_minutes=forecast_horizon_minutes)
            val = CityStateValidator.validate(c_state)
            if not val.is_valid:
                validation_failures += 1
            if save:
                aggregator.save_snapshot(c_state)
            generated_count += 1
            records.append(c_state.model_dump())

    return {
        "status": "success",
        "generated_count": generated_count,
        "validation_failures": validation_failures,
        "saved_to_db": save,
        "forecast_horizon_minutes": forecast_horizon_minutes,
        "spatial_unit_type": spatial_unit_type
    }
