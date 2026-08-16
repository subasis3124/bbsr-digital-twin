from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """
    Performs verification check verifying API is reachable,
    database is connected, and PostGIS extension is available.
    """
    health_status = {
        "status": "healthy",
        "database": "disconnected",
        "postgis": "unavailable",
        "postgis_version": None
    }
    
    try:
        # 1. Query check on DB connection
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
        
        # 2. Query check on PostGIS availability & version
        postgis_query = db.execute(text("SELECT PostGIS_Full_Version()")).scalar()
        if postgis_query:
            health_status["postgis"] = "available"
            health_status["postgis_version"] = postgis_query.split("[")[0].strip()
            
    except Exception as e:
        # If database connection fails, return 503 service unavailable
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
        
    return health_status
