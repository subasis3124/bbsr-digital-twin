from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
import shapely.geometry
from typing import List
from backend.app.database import get_db
from backend.app.models import City
from backend.app.schemas import CityOut, GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/cities", tags=["cities"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_cities(db: Session = Depends(get_db)):
    """
    Fetches all administrative cities in the database, serialized as a GeoJSON FeatureCollection.
    """
    cities = db.query(City).all()
    features = []
    
    for city in cities:
        shape = to_shape(city.geom)
        geom_geojson = shapely.geometry.mapping(shape)
        
        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": city.id,
                "name": city.name,
                "created_at": city.created_at.isoformat() if city.created_at else None,
                "updated_at": city.updated_at.isoformat() if city.updated_at else None,
            }
        )
        features.append(feature)
        
    return GeoJSONFeatureCollection(features=features)
