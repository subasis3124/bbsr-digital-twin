from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import (
    health, cities, wards, roads, buildings, hospitals, schools,
    police, fire_stations, bus_stops, water_bodies, bus_routes, flood_risk,
    traffic, air_quality, gnn_traffic, city_state, simulations, optimization,
    dashboard, ai
)

from backend.app.config import settings

app = FastAPI(
    title="BBSR Digital Twin API",
    description="Spatial API backend for urban planning, traffic, and flood simulations of Bhubaneswar, India.",
    version="1.0.0"
)

# Configure Cross-Origin Resource Sharing (CORS)
allowed_origins_list = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()] if settings.ALLOWED_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(health.router)
app.include_router(cities.router)
app.include_router(wards.router)
app.include_router(roads.router)
app.include_router(buildings.router)
app.include_router(hospitals.router)
app.include_router(schools.router)
app.include_router(police.router)
app.include_router(fire_stations.router)
app.include_router(bus_stops.router)
app.include_router(water_bodies.router)
app.include_router(bus_routes.router)
app.include_router(flood_risk.router)
app.include_router(traffic.router)
app.include_router(air_quality.router)
app.include_router(gnn_traffic.router)
app.include_router(city_state.router)
app.include_router(simulations.router)
app.include_router(optimization.router)
app.include_router(dashboard.router)
app.include_router(ai.router)









@app.get("/")
def read_root():
    return {
        "message": "Welcome to BBSR Digital Twin API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health"
    }
