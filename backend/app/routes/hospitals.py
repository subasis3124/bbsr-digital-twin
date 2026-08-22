from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import Hospital, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/hospitals", tags=["hospitals"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_hospitals(
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    name: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches healthcare facilities/hospitals as a GeoJSON FeatureCollection.
    Supports pagination, search by name, and spatial filtering by ward ID.
    """
    query = db.query(Hospital)
    
    if name:
        query = query.filter(Hospital.name.ilike(f"%{name}%"))
        
    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: hospital Point intersects ward geometry
        query = query.filter(ST_Intersects(Hospital.geom, ward.geom))
        
    hospitals = query.offset(offset).limit(limit).all()
    features = []
    
    for hospital in hospitals:
        shape = to_shape(hospital.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": hospital.id,
                "osm_id": int(hospital.osm_id) if hospital.osm_id else None,
                "name": hospital.name,
                "beds": hospital.beds,
                "created_at": hospital.created_at.isoformat() if hospital.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{hospital_id}", response_model=GeoJSONFeature)
def get_hospital_by_id(hospital_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific healthcare facility by its database ID, returning it as a single GeoJSON Feature.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID {hospital_id} not found"
        )
        
    shape = to_shape(hospital.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": hospital.id,
            "osm_id": int(hospital.osm_id) if hospital.osm_id else None,
            "name": hospital.name,
            "beds": hospital.beds,
            "created_at": hospital.created_at.isoformat() if hospital.created_at else None
        }
    )
