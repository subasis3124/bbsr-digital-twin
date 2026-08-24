import logging
import pandas as pd
from sqlalchemy import text
from backend.app.database import SessionLocal

logger = logging.getLogger("ML.FeatureExtractor")

class FeatureExtractor:
    """
    Extracts spatio-temporal features for the spatial_grid_cells in Bhubaneswar.
    Uses database-level spatial queries and PostGIS indices to compute distances.
    """
    def __init__(self):
        pass

    def extract_features(self) -> pd.DataFrame:
        """
        Executes an optimized SQL join query in PostGIS to fetch topography,
        population, and building/road/water proximity features.
        Returns:
            pd.DataFrame: Matrix containing cell_id and numerical features.
        """
        logger.info("Extracting spatial features from the database...")
        db = SessionLocal()
        
        query = text("""
            SELECT 
                c.id as cell_id,
                c.cell_code,
                ST_X(c.centroid) as lon,
                ST_Y(c.centroid) as lat,
                COALESCE(sf.elevation, 36.72) as elevation,
                COALESCE(sf.slope, 2.01) as slope,
                COALESCE(sf.ndvi, 0.52) as ndvi,
                COALESCE(sf.ndwi, -0.13) as ndwi,
                COALESCE(sf.ndbi, -0.25) as ndbi,
                COALESCE(p.population_count, 0) as population_count,
                COALESCE(
                    ST_Distance(c.centroid::geography, 
                                (SELECT w.geom FROM water_bodies w ORDER BY c.centroid <-> w.geom LIMIT 1)::geography), 
                    9999.0
                ) as dist_to_water,
                COALESCE(
                    ST_Distance(c.centroid::geography, 
                                (SELECT r.geom FROM roads r ORDER BY c.centroid <-> r.geom LIMIT 1)::geography), 
                    9999.0
                ) as dist_to_road,
                COALESCE(
                    ST_Distance(c.centroid::geography, 
                                (SELECT b.geom FROM buildings b ORDER BY c.centroid <-> b.geom LIMIT 1)::geography), 
                    9999.0
                ) as dist_to_building
            FROM spatial_grid_cells c
            LEFT JOIN satellite_features sf ON c.id = sf.cell_id AND sf.timestamp = '2026-01-01 00:00:00+00'
            LEFT JOIN population p ON ST_Intersects(p.geom, c.centroid)
        """)
        
        try:
            results = db.execute(query).fetchall()
            df = pd.DataFrame(results, columns=[
                "cell_id", "cell_code", "lon", "lat", 
                "elevation", "slope", "ndvi", "ndwi", "ndbi", 
                "population_count", "dist_to_water", "dist_to_road", "dist_to_building"
            ])
            logger.info(f"Successfully extracted features for {len(df)} grid cells.")
            
            # Clean numerical types
            numeric_cols = [
                "lon", "lat", "elevation", "slope", "ndvi", "ndwi", "ndbi", 
                "population_count", "dist_to_water", "dist_to_road", "dist_to_building"
            ]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                
            return df
        except Exception as e:
            logger.error(f"Failed to execute feature extraction query: {e}")
            raise
        finally:
            db.close()
