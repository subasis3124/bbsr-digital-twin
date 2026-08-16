from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any, Dict

# ==========================================
# GeoJSON Base Specification Schemas
# ==========================================

class GeoJSONGeometry(BaseModel):
    type: str = Field(..., example="Point")
    coordinates: Any = Field(..., example=[85.83, 20.27])

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


# ==========================================
# City Entity Schemas
# ==========================================

class CityBase(BaseModel):
    name: str = Field(default="Bhubaneswar")

class CityCreate(CityBase):
    geom_wkt: str = Field(..., description="WKT representation of the city boundary polygon")

class CityOut(CityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# GeoJSON customized output for City
class CityGeoJSON(GeoJSONFeature):
    pass


# ==========================================
# Ward Entity Schemas
# ==========================================

class WardBase(BaseModel):
    ward_number: int
    name: Optional[str] = None
    population_est: Optional[int] = None

class WardCreate(WardBase):
    geom_wkt: str = Field(..., description="WKT representation of the multi-polygon")

class WardOut(WardBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# GeoJSON customized output for Ward
class WardGeoJSON(GeoJSONFeature):
    pass
