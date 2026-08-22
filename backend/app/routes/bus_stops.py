from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import BusStop, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/bus-stops", tags=["bus-stops"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_bus_stops(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches bus stops as a GeoJSON FeatureCollection.
    Supports pagination, name search, and spatial filtering by ward ID.
    """
    query = db.query(BusStop)
    
    if name:
        query = query.filter(BusStop.name.ilike(f"%{name}%"))
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: bus stop Point intersects ward geometry
        query = query.filter(ST_Intersects(BusStop.geom, ward.geom))
        
    bus_stops = query.offset(offset).limit(limit).all()
    features = []
    
    for bs in bus_stops:
        shape = to_shape(bs.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": bs.id,
                "osm_id": int(bs.osm_id) if bs.osm_id else None,
                "name": bs.name,
                "created_at": bs.created_at.isoformat() if bs.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{bus_stop_id}", response_model=GeoJSONFeature)
def get_bus_stop_by_id(bus_stop_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific bus stop by its database ID, returning it as a single GeoJSON Feature.
    """
    bs = db.query(BusStop).filter(BusStop.id == bus_stop_id).first()
    if not bs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus stop with ID {bus_stop_id} not found"
        )
        
    shape = to_shape(bs.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": bs.id,
            "osm_id": int(bs.osm_id) if bs.osm_id else None,
            "name": bs.name,
            "created_at": bs.created_at.isoformat() if bs.created_at else None
        }
    )
