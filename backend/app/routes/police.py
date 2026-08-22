from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import PoliceStation, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/police", tags=["police"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_police_stations(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches police stations as a GeoJSON FeatureCollection.
    Supports pagination, name search, and spatial filtering by ward ID.
    """
    query = db.query(PoliceStation)
    
    if name:
        query = query.filter(PoliceStation.name.ilike(f"%{name}%"))
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: police station Point intersects ward geometry
        query = query.filter(ST_Intersects(PoliceStation.geom, ward.geom))
        
    police_stations = query.offset(offset).limit(limit).all()
    features = []
    
    for ps in police_stations:
        shape = to_shape(ps.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": ps.id,
                "osm_id": int(ps.osm_id) if ps.osm_id else None,
                "name": ps.name,
                "created_at": ps.created_at.isoformat() if ps.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{police_id}", response_model=GeoJSONFeature)
def get_police_station_by_id(police_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific police station by its database ID, returning it as a single GeoJSON Feature.
    """
    ps = db.query(PoliceStation).filter(PoliceStation.id == police_id).first()
    if not ps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Police station with ID {police_id} not found"
        )
        
    shape = to_shape(ps.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": ps.id,
            "osm_id": int(ps.osm_id) if ps.osm_id else None,
            "name": ps.name,
            "created_at": ps.created_at.isoformat() if ps.created_at else None
        }
    )
