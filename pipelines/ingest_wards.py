import os
import sys
import json
import logging
from shapely.geometry import shape, Polygon, MultiPolygon
from geoalchemy2.shape import from_shape

# Setup path logic to import backend modules cleanly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.database import SessionLocal
from backend.app.models import Ward

# Configure logging to standard output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ward_ingestion")

def validate_and_normalize_feature(feature: dict):
    """
    Validates a single GeoJSON feature representing a ward.
    Returns (ward_number, name, population_est, geom_shape) on success,
    or raises ValueError if validation fails.
    """
    properties = feature.get("properties", {})
    ward_str = properties.get("wardno")
    
    # 1. Validate wardno and convert WX -> X
    if not ward_str or not isinstance(ward_str, str) or not ward_str.startswith("W"):
        raise ValueError(f"Missing or invalid wardno key: {ward_str}")
    
    try:
        ward_number = int(ward_str.replace("W", "").strip())
    except ValueError:
        raise ValueError(f"Ward number portion is not numeric: {ward_str}")

    # 2. Validate population count
    total_pop = properties.get("totalwardp")
    if total_pop is None:
        raise ValueError("Missing totalwardp (population) attribute")
    try:
        population_est = int(total_pop)
    except (ValueError, TypeError):
        raise ValueError(f"Population value is not a valid integer: {total_pop}")

    # 3. Validate counselor name (noneofthec)
    name = properties.get("nameofthec")
    if name:
        name = str(name).strip()
    else:
        name = None

    # 4. Validate and construct Geometry
    geom_data = feature.get("geometry")
    if not geom_data:
        raise ValueError("Feature contains no geometry data")
    
    geom_shape = shape(geom_data)
    
    # Check geometry validity
    if not geom_shape.is_valid:
        raise ValueError("Geometry contains self-intersections or is invalid")

    # Verify geometry type is Polygon or MultiPolygon
    if not isinstance(geom_shape, (Polygon, MultiPolygon)):
        raise ValueError(f"Unsupported geometry type: {geom_shape.geom_type}")

    # Convert Polygon to MultiPolygon
    if isinstance(geom_shape, Polygon):
        geom_shape = MultiPolygon([geom_shape])

    return ward_number, name, population_est, geom_shape

def ingest_wards(geojson_path: str):
    """
    Ingests ward geometries and attributes from a geojson file into the wards table.
    Ensures validation and idempotency (updates existing, inserts new).
    """
    if not os.path.exists(geojson_path):
        logger.error(f"GeoJSON file not found at: {geojson_path}")
        sys.exit(1)

    logger.info(f"Opening GeoJSON file: {geojson_path}")
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    total_features = len(features)
    logger.info(f"Loading {total_features} features...")

    db = SessionLocal()
    
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    try:
        for index, feature in enumerate(features, start=1):
            ward_str = feature.get("properties", {}).get("wardno")
            try:
                # Validate and normalize
                ward_number, name, population_est, geom_shape = validate_and_normalize_feature(feature)

                # DB Ingestion logic (Idempotent Upsert)
                existing_ward = db.query(Ward).filter(Ward.ward_number == ward_number).first()
                
                if existing_ward:
                    existing_ward.name = name
                    existing_ward.population_est = population_est
                    existing_ward.geom = from_shape(geom_shape, srid=4326)
                    updated += 1
                else:
                    new_ward = Ward(
                        ward_number=ward_number,
                        name=name,
                        population_est=population_est,
                        geom=from_shape(geom_shape, srid=4326)
                    )
                    db.add(new_ward)
                    inserted += 1

            except Exception as fe:
                errors += 1
                logger.error(f"Error validating feature {index} (wardno: {ward_str}): {fe}")
                continue

        # Commit transaction
        if errors > 0:
            logger.warning(f"Processing finished with {errors} validation errors. Proceeding to commit valid features.")
        
        db.commit()
        logger.info("Database transaction committed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Catastrophic error during ingestion transaction: {e}. Transaction rolled back.")
        raise e
    finally:
        db.close()

    # Final summary output
    logger.info(f"Validated {total_features} features")
    logger.info(f"Inserted: {inserted}")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Errors: {errors}")

if __name__ == "__main__":
    geojson_file = os.path.join(project_root, "data", "raw", "boundaries", "bmc_wards.geojson")
    ingest_wards(geojson_file)
