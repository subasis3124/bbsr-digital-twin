from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import Road
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/roads", tags=["roads"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_roads(
    limit: int = Query(default=2000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    highway_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches roads from the database as a GeoJSON FeatureCollection.
    Supports basic limit/offset pagination and filtering by highway type.
    """
    query = db.query(Road)
    if highway_type:
        query = query.filter(Road.highway_type == highway_type)
        
    roads = query.offset(offset).limit(limit).all()
    features = []
    
    for road in roads:
        shape = to_shape(road.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": road.id,
                "osm_id": int(road.osm_id) if road.osm_id else None,
                "name": road.name,
                "highway_type": road.highway_type,
                "lanes": road.lanes,
                "maxspeed": road.maxspeed,
                "oneway": road.oneway,
                "created_at": road.created_at.isoformat() if road.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{road_id}", response_model=GeoJSONFeature)
def get_road_by_id(road_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific road by its database ID, returning it as a single GeoJSON Feature.
    """
    road = db.query(Road).filter(Road.id == road_id).first()
    if not road:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Road with ID {road_id} not found"
        )
        
    shape = to_shape(road.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": road.id,
            "osm_id": int(road.osm_id) if road.osm_id else None,
            "name": road.name,
            "highway_type": road.highway_type,
            "lanes": road.lanes,
            "maxspeed": road.maxspeed,
            "oneway": road.oneway,
            "created_at": road.created_at.isoformat() if road.created_at else None
        }
    )
