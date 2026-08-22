import os
import sys
import json
import logging
import re
from shapely.geometry import shape, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.prepared import prep
from geoalchemy2.shape import from_shape, to_shape

# Setup path logic to import backend modules cleanly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.database import SessionLocal
from backend.app.models import Ward, Road

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("road_ingestion")

def parse_lanes(lanes_val):
    """
    Extracts number of lanes safely.
    """
    if lanes_val is None:
        return None
    if isinstance(lanes_val, int):
        return lanes_val
    match = re.search(r'\d+', str(lanes_val))
    if match:
        return int(match.group())
    return None

def parse_maxspeed(speed_val):
    """
    Extracts speed limit as integer, converting mph to km/h if needed.
    """
    if speed_val is None:
        return None
    if isinstance(speed_val, (int, float)):
        return int(speed_val)
    speed_str = str(speed_val).strip().lower()
    match = re.search(r'\d+', speed_str)
    if match:
        val = int(match.group())
        if "mph" in speed_str:
            val = int(val * 1.609)
        return val
    return None

def parse_oneway(oneway_val):
    """
    Converts oneway tag value to boolean.
    """
    if oneway_val is None:
        return False
    if isinstance(oneway_val, bool):
        return oneway_val
    val_str = str(oneway_val).strip().lower()
    return val_str in ("yes", "1", "true")

def ingest_roads(json_path: str):
    """
    Ingests road ways from an OpenStreetMap raw Overpass JSON file into the database.
    Performs boundary filtering, validation, and idempotent bulk upsert.
    """
    logger.info("Road ingestion started...")

    if not os.path.exists(json_path):
        logger.error(f"Source JSON file not found at: {json_path}")
        sys.exit(1)

    logger.info(f"Opening OSM raw file: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    total_elements = len(elements)
    logger.info(f"Features read: {total_elements}")

    db = SessionLocal()

    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0
    errors = 0
    geographically_relevant = 0

    try:
        # Load BMC ward boundaries to create unified spatial boundary
        logger.info("Loading BMC ward boundaries from database...")
        wards = db.query(Ward).all()
        if not wards:
            logger.error("No ward boundaries found in database. Please run ward ingestion first.")
            sys.exit(1)
        
        ward_shapes = [to_shape(w.geom) for w in wards]
        bmc_boundary = unary_union(ward_shapes)
        prepared_boundary = prep(bmc_boundary)
        logger.info(f"Successfully loaded and unioned {len(wards)} wards.")

        # Batch buffer for upserts
        batch_size = 1000
        
        for index in range(0, total_elements, batch_size):
            batch_elements = elements[index:index+batch_size]
            
            # Fetch existing road osm_ids in the current batch to implement upsert strategy
            osm_ids_in_batch = []
            for elem in batch_elements:
                osm_id = elem.get("id")
                if osm_id is not None:
                    osm_ids_in_batch.append(osm_id)
            
            existing_roads = db.query(Road).filter(Road.osm_id.in_(osm_ids_in_batch)).all()
            existing_map = {int(r.osm_id): r for r in existing_roads}
            
            for elem in batch_elements:
                osm_id = elem.get("id")
                tags = elem.get("tags", {})
                geometry_nodes = elem.get("geometry", [])

                try:
                    if osm_id is None:
                        invalid += 1
                        continue

                    # Validate geometry exists
                    if not geometry_nodes or len(geometry_nodes) < 2:
                        invalid += 1
                        continue

                    # Construct Shapely geometry
                    coords = [(node["lon"], node["lat"]) for node in geometry_nodes]
                    geom_shape = LineString(coords)

                    # Validate geometry coordinates ring / self-intersection
                    if not geom_shape.is_valid:
                        invalid += 1
                        continue

                    # Filter Geographically: must intersect the BMC ward boundaries
                    if not prepared_boundary.intersects(geom_shape):
                        skipped += 1
                        continue
                    
                    geographically_relevant += 1

                    # Parse values
                    name = tags.get("name")
                    if name:
                        name = str(name).strip()
                    else:
                        name = None

                    highway_type = tags.get("highway")
                    if highway_type:
                        highway_type = str(highway_type).strip()

                    lanes = parse_lanes(tags.get("lanes"))
                    maxspeed = parse_maxspeed(tags.get("maxspeed"))
                    oneway = parse_oneway(tags.get("oneway"))

                    # Perform Upsert
                    if osm_id in existing_map:
                        road = existing_map[osm_id]
                        road.name = name
                        road.highway_type = highway_type
                        road.lanes = lanes if lanes is not None else 1
                        road.maxspeed = maxspeed
                        road.oneway = oneway
                        road.geom = from_shape(geom_shape, srid=4326)
                        updated += 1
                    else:
                        new_road = Road(
                            osm_id=osm_id,
                            name=name,
                            highway_type=highway_type,
                            lanes=lanes if lanes is not None else 1,
                            maxspeed=maxspeed,
                            oneway=oneway,
                            geom=from_shape(geom_shape, srid=4326)
                        )
                        db.add(new_road)
                        inserted += 1

                except Exception as fe:
                    errors += 1
                    logger.error(f"Error processing OSM way {osm_id}: {fe}")
                    continue

            # Commit batch
            db.commit()

        logger.info("Database transaction committed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Catastrophic error during ingestion transaction: {e}. Transaction rolled back.")
        raise e
    finally:
        db.close()

    # Log summary statistics
    logger.info(f"Features geographically relevant: {geographically_relevant}")
    logger.info(f"Inserted: {inserted}")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Invalid: {invalid}")
    logger.info(f"Errors: {errors}")
    logger.info("Road ingestion completed successfully.")

if __name__ == "__main__":
    raw_file = os.path.join(project_root, "data", "raw", "infrastructure", "bhubaneswar_roads.json")
    ingest_roads(raw_file)
