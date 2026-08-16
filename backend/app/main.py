from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import health, cities, wards

app = FastAPI(
    title="BBSR Digital Twin API",
    description="Spatial API backend for urban planning, traffic, and flood simulations of Bhubaneswar, India.",
    version="1.0.0"
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows our Next.js frontend to securely query the API from different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(health.router)
app.include_router(cities.router)
app.include_router(wards.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to BBSR Digital Twin API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health"
    }
