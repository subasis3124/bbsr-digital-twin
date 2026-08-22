from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import FireStation, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/fire-stations", tags=["fire-stations"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_fire_stations(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches fire stations as a GeoJSON FeatureCollection.
    Supports pagination, name search, and spatial filtering by ward ID.
    """
    query = db.query(FireStation)
    
    if name:
        query = query.filter(FireStation.name.ilike(f"%{name}%"))
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: fire station Point intersects ward geometry
        query = query.filter(ST_Intersects(FireStation.geom, ward.geom))
        
    fire_stations = query.offset(offset).limit(limit).all()
    features = []
    
    for fs in fire_stations:
        shape = to_shape(fs.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": fs.id,
                "osm_id": int(fs.osm_id) if fs.osm_id else None,
                "name": fs.name,
                "created_at": fs.created_at.isoformat() if fs.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{fire_station_id}", response_model=GeoJSONFeature)
def get_fire_station_by_id(fire_station_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific fire station by its database ID, returning it as a single GeoJSON Feature.
    """
    fs = db.query(FireStation).filter(FireStation.id == fire_station_id).first()
    if not fs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fire station with ID {fire_station_id} not found"
        )
        
    shape = to_shape(fs.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": fs.id,
            "osm_id": int(fs.osm_id) if fs.osm_id else None,
            "name": fs.name,
            "created_at": fs.created_at.isoformat() if fs.created_at else None
        }
    )
