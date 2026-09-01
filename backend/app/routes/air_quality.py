from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects, ST_MakeEnvelope
import shapely.geometry
from typing import Optional, List
from datetime import datetime

from backend.app.database import get_db
from backend.app.models import AirQualityPrediction
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/air-quality", tags=["air_quality"])

SCIENTIFIC_WARNING = (
    "WARNING: This forecast was generated using synthetic validation data "
    "because sufficient historical air-quality observations are currently unavailable."
)

@router.get("", response_model=GeoJSONFeatureCollection)
def get_air_quality_forecasts(
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    station_name: Optional[str] = Query(default=None),
    pollutant: Optional[str] = Query(default=None),
    horizon_hours: Optional[int] = Query(default=None),
    forecast_issue_time: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Fetches air quality multi-step forecasts as a GeoJSON FeatureCollection.
    Supports viewport bounding box queries, station filtering, pollutant selection (PM2.5, PM10),
    forecast horizon selection (6h, 12h, 24h), and offset/limit pagination.
    """
    query = db.query(AirQualityPrediction)

    # 1. Bounding box spatial filter
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
        query = query.filter(ST_Intersects(AirQualityPrediction.geom, envelope))

    # 2. Filters
    if station_name:
        query = query.filter(AirQualityPrediction.station_name.ilike(f"%{station_name}%"))

    if pollutant:
        query = query.filter(AirQualityPrediction.pollutant.ilike(pollutant))

    if horizon_hours is not None:
        if horizon_hours not in [6, 12, 24]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported forecast horizon. Valid horizons are 6, 12, or 24 hours."
            )
        query = query.filter(AirQualityPrediction.horizon_hours == horizon_hours)

    if forecast_issue_time:
        try:
            target_dt = datetime.fromisoformat(forecast_issue_time.replace("Z", "+00:00"))
            query = query.filter(AirQualityPrediction.forecast_issue_time == target_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid forecast_issue_time ISO format."
            )

    predictions = query.order_by(AirQualityPrediction.target_time.asc()).offset(offset).limit(limit).all()

    features = []
    for pred in predictions:
        if pred.geom is not None:
            shape = to_shape(pred.geom)
            geom_geojson = shapely.geometry.mapping(shape)
        else:
            # Default point for Bhubaneswar Central if geom is missing
            geom_geojson = {"type": "Point", "coordinates": [85.824, 20.296]}

        properties = {
            "prediction_id": pred.id,
            "station_name": pred.station_name,
            "pollutant": pred.pollutant,
            "forecast_issue_time": pred.forecast_issue_time.isoformat() if pred.forecast_issue_time else None,
            "target_time": pred.target_time.isoformat() if pred.target_time else None,
            "horizon_hours": pred.horizon_hours,
            "predicted_value": float(pred.predicted_value),
            "aqi_sub_index": pred.aqi_sub_index,
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

@router.get("/{forecast_id}", response_model=GeoJSONFeature)
def get_air_quality_forecast_by_id(forecast_id: int, db: Session = Depends(get_db)):
    """
    Retrieves specific air quality forecast details by forecast ID.
    """
    pred = db.query(AirQualityPrediction).filter(AirQualityPrediction.id == forecast_id).first()

    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Air Quality forecast ID {forecast_id} not found."
        )

    if pred.geom is not None:
        shape = to_shape(pred.geom)
        geom_geojson = shapely.geometry.mapping(shape)
    else:
        geom_geojson = {"type": "Point", "coordinates": [85.824, 20.296]}

    properties = {
        "prediction_id": pred.id,
        "station_name": pred.station_name,
        "pollutant": pred.pollutant,
        "forecast_issue_time": pred.forecast_issue_time.isoformat() if pred.forecast_issue_time else None,
        "target_time": pred.target_time.isoformat() if pred.target_time else None,
        "horizon_hours": pred.horizon_hours,
        "predicted_value": float(pred.predicted_value),
        "aqi_sub_index": pred.aqi_sub_index,
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
