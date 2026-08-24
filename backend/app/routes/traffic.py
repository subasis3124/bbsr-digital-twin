from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects, ST_MakeEnvelope
import shapely.geometry
from typing import Optional, List
from datetime import datetime

from backend.app.database import get_db
from backend.app.models import Road, TrafficPrediction
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/traffic", tags=["traffic"])

SCIENTIFIC_WARNING = (
    "WARNING: This traffic forecasting classification is generated using synthetic validation "
    "labels because a defensible historical traffic target dataset is currently unavailable."
)

@router.get("", response_model=GeoJSONFeatureCollection)
def get_traffic_predictions(
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    road_id: Optional[int] = Query(default=None),
    forecast_horizon_minutes: Optional[int] = Query(default=None),
    prediction_time: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Fetches traffic forecasting predictions joined with road geometries as a GeoJSON FeatureCollection.
    Supports viewport bounding box queries, road ID filtering, target prediction times, and pagination limits.
    """
    # Build query joining predictions to road segments for geometry details
    query = db.query(TrafficPrediction).join(Road, TrafficPrediction.road_id == Road.id)
    
    # 1. Bounding box spatial bounding viewport crop
    bbox_params = [min_lon, min_lat, max_lon, max_lat]
    if any(p is not None for p in bbox_params):
        if not all(p is not None for p in bbox_params):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All bounding box parameters (min_lon, min_lat, max_lon, max_lat) must be specified for viewport filtering."
            )
        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bounding box corners: min coordinates must be smaller than max coordinates."
            )
        
        envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = query.filter(ST_Intersects(Road.geom, envelope))
        
    # 2. Key filters
    if road_id is not None:
        query = query.filter(TrafficPrediction.road_id == road_id)
        
    if forecast_horizon_minutes is not None:
        query = query.filter(TrafficPrediction.forecast_horizon_minutes == forecast_horizon_minutes)
        
    if prediction_time:
        try:
            target_dt = datetime.fromisoformat(prediction_time.replace("Z", "+00:00"))
            query = query.filter(TrafficPrediction.prediction_time == target_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid prediction_time ISO sequence format."
            )
            
    # Apply offset/limit pagination
    predictions = query.offset(offset).limit(limit).all()
    
    features = []
    for pred in predictions:
        road = pred.road
        shape = to_shape(road.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        # Include data provenance metadata
        properties = {
            "prediction_id": pred.id,
            "road_id": pred.road_id,
            "osm_id": int(road.osm_id) if road.osm_id else None,
            "name": road.name,
            "highway_type": road.highway_type,
            "lanes": road.lanes,
            "maxspeed": road.maxspeed,
            "prediction_time": pred.prediction_time.isoformat() if pred.prediction_time else None,
            "forecast_horizon_minutes": pred.forecast_horizon_minutes,
            "predicted_speed": float(pred.predicted_speed),
            "predicted_congestion_ratio": float(pred.predicted_congestion_ratio) if pred.predicted_congestion_ratio is not None else None,
            "model_name": pred.model_name,
            "model_version": pred.model_version,
            "is_synthetic": pred.is_synthetic,
            "data_provenance_status": pred.data_provenance_status,
            "created_at": pred.created_at.isoformat() if pred.created_at else None
        }
        
        if pred.is_synthetic:
            properties["scientific_validation_warning"] = SCIENTIFIC_WARNING
            
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties=properties
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{road_id}", response_model=GeoJSONFeature)
def get_traffic_prediction_by_road(road_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the latest traffic segment forecasts details for a specific road ID.
    """
    pred = db.query(TrafficPrediction).filter(TrafficPrediction.road_id == road_id).order_by(TrafficPrediction.prediction_time.desc()).first()
    
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traffic predictions for Road ID {road_id} not found."
        )
        
    road = pred.road
    shape = to_shape(road.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    properties = {
        "prediction_id": pred.id,
        "road_id": pred.road_id,
        "osm_id": int(road.osm_id) if road.osm_id else None,
        "name": road.name,
        "highway_type": road.highway_type,
        "lanes": road.lanes,
        "maxspeed": road.maxspeed,
        "prediction_time": pred.prediction_time.isoformat() if pred.prediction_time else None,
        "forecast_horizon_minutes": pred.forecast_horizon_minutes,
        "predicted_speed": float(pred.predicted_speed),
        "predicted_congestion_ratio": float(pred.predicted_congestion_ratio) if pred.predicted_congestion_ratio is not None else None,
        "model_name": pred.model_name,
        "model_version": pred.model_version,
        "is_synthetic": pred.is_synthetic,
        "data_provenance_status": pred.data_provenance_status,
        "created_at": pred.created_at.isoformat() if pred.created_at else None
    }
    
    if pred.is_synthetic:
        properties["scientific_validation_warning"] = SCIENTIFIC_WARNING
        
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties=properties
    )
