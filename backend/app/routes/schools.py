from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import School, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/schools", tags=["schools"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_schools(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    institution_type: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches educational institutions as a GeoJSON FeatureCollection.
    Supports pagination, name search, filtering by institution type, and spatial filtering by ward ID.
    """
    query = db.query(School)
    
    if name:
        query = query.filter(School.name.ilike(f"%{name}%"))
        
    if institution_type:
        query = query.filter(School.institution_type == institution_type)
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: school Point intersects ward geometry
        query = query.filter(ST_Intersects(School.geom, ward.geom))
        
    schools = query.offset(offset).limit(limit).all()
    features = []
    
    for school in schools:
        shape = to_shape(school.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": school.id,
                "osm_id": int(school.osm_id) if school.osm_id else None,
                "name": school.name,
                "institution_type": school.institution_type,
                "created_at": school.created_at.isoformat() if school.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{school_id}", response_model=GeoJSONFeature)
def get_school_by_id(school_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific educational institution by its database ID, returning it as a single GeoJSON Feature.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"School with ID {school_id} not found"
        )
        
    shape = to_shape(school.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": school.id,
            "osm_id": int(school.osm_id) if school.osm_id else None,
            "name": school.name,
            "institution_type": school.institution_type,
            "created_at": school.created_at.isoformat() if school.created_at else None
        }
    )
