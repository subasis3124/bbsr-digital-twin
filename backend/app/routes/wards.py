from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
import shapely.geometry
from backend.app.database import get_db
from backend.app.models import Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/wards", tags=["wards"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_wards(db: Session = Depends(get_db)):
    """
    Fetches all administrative wards, serialized as a GeoJSON FeatureCollection.
    """
    wards = db.query(Ward).all()
    features = []
    
    for ward in wards:
        shape = to_shape(ward.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": ward.id,
                "ward_number": ward.ward_number,
                "name": ward.name,
                "population_est": ward.population_est,
                "created_at": ward.created_at.isoformat() if ward.created_at else None
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)

@router.get("/{ward_id}", response_model=GeoJSONFeature)
def get_ward_by_id(ward_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific ward by its internal database ID, returning it as a single GeoJSON Feature.
    """
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward with ID {ward_id} not found"
        )
        
    shape = to_shape(ward.geom)
    geom_geojson = shapely.geometry.mapping(shape)
    
    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": ward.id,
            "ward_number": ward.ward_number,
            "name": ward.name,
            "population_est": ward.population_est,
            "created_at": ward.created_at.isoformat() if ward.created_at else None
        }
    )
