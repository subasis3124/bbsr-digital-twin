from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_Intersects
import shapely.geometry
from typing import Optional
from backend.app.database import get_db
from backend.app.models import BusRoute, Ward
from backend.app.schemas import GeoJSONFeatureCollection, GeoJSONFeature

router = APIRouter(prefix="/api/v1/bus-routes", tags=["bus-routes"])

@router.get("", response_model=GeoJSONFeatureCollection)
def get_bus_routes(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    route_name: Optional[str] = Query(default=None),
    operator: Optional[str] = Query(default=None),
    ward_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Fetches bus routes as a GeoJSON FeatureCollection.
    Supports pagination, route_name search, operator match, and spatial filtering by ward ID.
    """
    query = db.query(BusRoute)

    if route_name:
        query = query.filter(BusRoute.route_name.ilike(f"%{route_name}%"))

    if operator:
        query = query.filter(BusRoute.operator.ilike(f"%{operator}%"))

    if ward_id:
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if not ward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ward with ID {ward_id} not found"
            )
        # Spatial filtering: bus route LineString intersects ward MultiPolygon geometry
        query = query.filter(ST_Intersects(BusRoute.geom, ward.geom))

    bus_routes = query.offset(offset).limit(limit).all()
    features = []

    for br in bus_routes:
        shape = to_shape(br.geom)
        geom_geojson = shapely.geometry.mapping(shape)

        feature = GeoJSONFeature(
            type="Feature",
            geometry=geom_geojson,
            properties={
                "id": br.id,
                "route_name": br.route_name,
                "operator": br.operator,
                "created_at": br.created_at.isoformat() if br.created_at else None
            }
        )
        features.append(feature)

    return GeoJSONFeatureCollection(features=features)

@router.get("/{route_id}", response_model=GeoJSONFeature)
def get_bus_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """
    Fetches a specific bus route by its database ID, returning it as a single GeoJSON Feature.
    """
    br = db.query(BusRoute).filter(BusRoute.id == route_id).first()
    if not br:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bus route with ID {route_id} not found"
        )

    shape = to_shape(br.geom)
    geom_geojson = shapely.geometry.mapping(shape)

    return GeoJSONFeature(
        type="Feature",
        geometry=geom_geojson,
        properties={
            "id": br.id,
            "route_name": br.route_name,
            "operator": br.operator,
            "created_at": br.created_at.isoformat() if br.created_at else None
        }
    )
