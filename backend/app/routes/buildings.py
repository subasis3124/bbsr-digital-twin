from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import Building, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/buildings", tags=["buildings"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_buildings(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    building_type: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches building footprints as a GeoJSON FeatureCollection.
    Supports pagination, filtering by building type, and spatial filtering by ward ID.
    """
    query = db.query(Building)
    
    if building_type:
        query = query.filter(Building.building_type == building_type)
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: building footprint intersects ward geometry
        query = query.filter(ST_Intersects(Building.geom, ward.geom))
        
    buildings = query.offset(offset).limit(limit).all()
    features = []
    
    for building in buildings:
        shape = to_shape(building.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": building.id,
                "osm_id": int(building.osm_id) if building.osm_id else None,
                "building_type": building.building_type,
                "height": float(building.height) if building.height else None,
                "levels": building.levels,
                "created_at": building.created_at.isoformat() if building.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{building_id}", response_model=GeoJSONFeature)
def get_building_by_id(building_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific building by its database ID, returning it as a single GeoJSON Feature.
    """
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with ID {building_id} not found"
        )
        
    shape = to_shape(building.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": building.id,
            "osm_id": int(building.osm_id) if building.osm_id else None,
            "building_type": building.building_type,
            "height": float(building.height) if building.height else None,
            "levels": building.levels,
            "created_at": building.created_at.isoformat() if building.created_at else None
        }
    )
