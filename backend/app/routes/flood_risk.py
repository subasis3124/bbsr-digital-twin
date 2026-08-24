from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional

from backend.app.database import get_db
from backend.app.models import Prediction, SpatialGridCell, FloodEvent, SatelliteFeature, PopulationGrid
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/flood-risk", tags=["flood-risk"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_flood_risk(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    risk_level: Optional[str] = Query(default=None, description="Filter predictions by risk category (LOW, MEDIUM, HIGH, VERY HIGH)"),
    model_name: Optional[str] = Query(default=None),
    model_version: Optional[str] = Query(default=None),
    min_lon: Optional[float] = Query(default=None),
    min_lat: Optional[float] = Query(default=None),
    max_lon: Optional[float] = Query(default=None),
    max_lat: Optional[float] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches flood risk predictions as a GeoJSON FeatureCollection.
    Supports viewport/bounding-box spatial filtering, risk category filtering, and model version overrides.
    """
    # Verify bounding box inputs consistency
    bbox_coords = [min_lon, min_lat, max_lon, max_lat]
    provided_coords = [c is not None for c in bbox_coords]
    
    if any(provided_coords) and not all(provided_coords):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="To filter by viewport bounding-box, all 4 coordinates (min_lon, min_lat, max_lon, max_lat) must be provided."
        )
    
    # Query linking Predictions and their Grid Cell geometries
    query = db.query(Prediction, SpatialGridCell).join(
        SpatialGridCell, Prediction.cell_id == SpatialGridCell.id
    )
    
    if risk_level:
        query = query.filter(func.upper(Prediction.predicted_class) == risk_level.upper())
        
    if model_name:
        query = query.filter(Prediction.model_name == model_name)
        
    if model_version:
        query = query.filter(Prediction.model_version == model_version)
        
    if all(provided_coords):
        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid bounding box. Coordinates must verify min_lon <= max_lon and min_lat <= max_lat."
            )
        
        # Spatial bbox filter using ST_Intersects and ST_MakeEnvelope (SRID 4326)
        query = query.filter(
            ST_Intersects(
                SpatialGridCell.geom,
                func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            )
        )
        
    # Execute query
    results = query.offset(offset).limit(limit).all()
    
    # Check if database has any historical flood observation records.
    is_synthetic = (db.query(FloodEvent).count() == 0)
    data_provenance = "synthetic_fallback" if is_synthetic else "validated_model"
    scientific_warning = (
        "WARNING: This flood risk classification is generated using synthetic validation labels "
        "because a defensible historical flood target dataset is currently unavailable."
        if is_synthetic else None
    )
    
    features = []
    for pred, cell in results:
        shape = to_shape(cell.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "prediction_id": pred.id,
                "cell_id": pred.cell_id,
                "cell_code": cell.cell_code,
                "model_name": pred.model_name,
                "model_version": pred.model_version,
                "prediction_time": pred.prediction_time.isoformat() if pred.prediction_time else None,
                "predicted_probability": float(pred.predicted_probability),
                "predicted_class": pred.predicted_class,
                "is_synthetic": is_synthetic,
                "data_provenance_status": data_provenance,
                "scientific_validation_warning": scientific_warning
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{prediction_id}", response_model=GeoJSONFeature)
def get_prediction_by_id(prediction_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific prediction cell by database ID including SHAP features attributions and satellite telemetry features.
    """
    result = db.query(Prediction, SpatialGridCell).join(
        SpatialGridCell, Prediction.cell_id == SpatialGridCell.id
    ).filter(Prediction.id == prediction_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flood risk prediction with ID {prediction_id} not found."
        )
        
    pred, cell = result
    
    # Query newest satellite feature
    sat_feat = db.query(SatelliteFeature).filter(
        SatelliteFeature.cell_id == cell.id
    ).order_by(SatelliteFeature.timestamp.desc()).first()
    
    # Query population for this cell (using centroid intersection)
    pop_record = db.query(PopulationGrid).filter(
        ST_Intersects(PopulationGrid.geom, cell.centroid)
    ).first()
    pop_count = pop_record.population_count if pop_record else None
    
    # Query if database has any historical flood observation records
    is_synthetic = (db.query(FloodEvent).count() == 0)
    data_provenance = "synthetic_fallback" if is_synthetic else "validated_model"
    scientific_warning = (
        "WARNING: This flood risk classification is generated using synthetic validation labels "
        "because a defensible historical flood target dataset is currently unavailable."
        if is_synthetic else None
    )
    
    shape = to_shape(cell.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    properties = {
        "prediction_id": pred.id,
        "cell_id": pred.cell_id,
        "cell_code": cell.cell_code,
        "model_name": pred.model_name,
        "model_version": pred.model_version,
        "prediction_time": pred.prediction_time.isoformat() if pred.prediction_time else None,
        "predicted_probability": float(pred.predicted_probability),
        "predicted_class": pred.predicted_class,
        "is_synthetic": is_synthetic,
        "data_provenance_status": data_provenance,
        "scientific_validation_warning": scientific_warning,
        "feature_importance_shap": pred.feature_importance_shap or {},
        "environmental_features": {
            "elevation_m": float(sat_feat.elevation) if sat_feat and sat_feat.elevation else None,
            "slope_deg": float(sat_feat.slope) if sat_feat and sat_feat.slope else None,
            "ndvi": float(sat_feat.ndvi) if sat_feat and sat_feat.ndvi else None,
            "ndwi": float(sat_feat.ndwi) if sat_feat and sat_feat.ndwi else None,
            "ndbi": float(sat_feat.ndbi) if sat_feat and sat_feat.ndbi else None,
            "population_count": pop_count
        }
    }
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties=properties
    )
