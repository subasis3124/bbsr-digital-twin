from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import WaterBody, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/water-bodies", tags=["water-bodies"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_water_bodies(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    water_type: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches water bodies as a GeoJSON FeatureCollection.
    Supports pagination, name search, and spatial filtering by ward ID.
    """
    query = db.query(WaterBody)
    
    if name:
        query = query.filter(WaterBody.name.ilike(f"%{name}%"))

    if water_type:
        query = query.filter(WaterBody.water_type == water_type)
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: water body Polygon intersects ward geometry
        query = query.filter(ST_Intersects(WaterBody.geom, ward.geom))
        
    water_bodies = query.offset(offset).limit(limit).all()
    features = []
    
    for wb in water_bodies:
        shape = to_shape(wb.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": wb.id,
                "osm_id": int(wb.osm_id) if wb.osm_id else None,
                "name": wb.name,
                "water_type": wb.water_type,
                "created_at": wb.created_at.isoformat() if wb.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{water_body_id}", response_model=GeoJSONFeature)
def get_water_body_by_id(water_body_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific water body by its database ID, returning it as a single GeoJSON Feature.
    """
    wb = db.query(WaterBody).filter(WaterBody.id == water_body_id).first()
    if not wb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Water body with ID {water_body_id} not found"
        )
        
    shape = to_shape(wb.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": wb.id,
            "osm_id": int(wb.osm_id) if wb.osm_id else None,
            "name": wb.name,
            "water_type": wb.water_type,
            "created_at": wb.created_at.isoformat() if wb.created_at else None
        }
    )
