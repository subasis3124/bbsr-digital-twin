import os
import sys
import json
import logging
import re
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.prepared import prep
from geoalchemy2.shape import from_shape, to_shape

# Setup path logic to import backend modules cleanly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.database import SessionLocal
from backend.app.models import Ward, Building

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("building_ingestion")

def parse_height(height_val):
    """
    Safely parses building height string into a float.
    Strips units like "m" or "meters".
    """
    if height_val is None:
        return None
    if isinstance(height_val, (int, float)):
        return float(height_val)
    val_str = str(height_val).strip().lower()
    match = re.search(r'^\d+(\.\d+)?', val_str)
    if match:
        return float(match.group())
    return None

def parse_levels(levels_val):
    """
    Safely parses building levels string into an integer.
    """
    if levels_val is None:
        return None
    if isinstance(levels_val, int):
        return levels_val
    val_str = str(levels_val).strip()
    match = re.search(r'\d+', val_str)
    if match:
        return int(match.group())
    return None

def ingest_buildings(json_path: str):
    """
    Ingests building footprints from raw OSM JSON into the database.
    Performs ward boundary filtering, validation, polygon normalization, and idempotent bulk upsert.
    """
    logger.info("Building ingestion started...")

    if not os.path.exists(json_path):
        logger.error(f"Source JSON file not found at: {json_path}")
        sys.exit(1)

    logger.info(f"Opening OSM raw file: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    total_elements = len(elements)
    logger.info(f"Raw features: {total_elements}")

    db = SessionLocal()

    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0
    errors = 0
    bmc_relevant = 0

    try:
        # Load BMC ward boundaries to construct the unified boundary filter
        logger.info("Loading BMC ward boundaries from database...")
        wards = db.query(Ward).all()
        if not wards:
            logger.error("No ward boundaries found in database. Please run ward ingestion first.")
            sys.exit(1)
        
        ward_shapes = [to_shape(w.geom) for w in wards]
        bmc_boundary = unary_union(ward_shapes)
        prepared_boundary = prep(bmc_boundary)
        logger.info(f"Successfully loaded and unioned {len(wards)} wards.")

        # Batch upsert settings
        batch_size = 1000
        
        for index in range(0, total_elements, batch_size):
            batch_elements = elements[index:index+batch_size]
            
            # Fetch existing building osm_ids in the current batch
            osm_ids_in_batch = []
            for elem in batch_elements:
                osm_id = elem.get("id")
                if osm_id is not None:
                    osm_ids_in_batch.append(osm_id)
            
            existing_buildings = db.query(Building).filter(Building.osm_id.in_(osm_ids_in_batch)).all()
            existing_map = {int(b.osm_id): b for b in existing_buildings}
            
            for elem in batch_elements:
                osm_id = elem.get("id")
                elem_type = elem.get("type")
                tags = elem.get("tags", {})

                try:
                    if osm_id is None:
                        invalid += 1
                        continue

                    geom_shape = None
                    if elem_type == "way":
                        geometry_nodes = elem.get("geometry", [])
                        if geometry_nodes and len(geometry_nodes) >= 3:
                            coords = [(node["lon"], node["lat"]) for node in geometry_nodes]
                            if coords[0] != coords[-1]:
                                coords.append(coords[0])
                            geom_shape = Polygon(coords)
                    elif elem_type == "relation":
                        members = elem.get("members", [])
                        outer_polys = []
                        for member in members:
                            if member.get("role") == "outer":
                                nodes = member.get("geometry", [])
                                if nodes and len(nodes) >= 3:
                                    coords = [(n["lon"], n["lat"]) for n in nodes]
                                    if coords[0] != coords[-1]:
                                        coords.append(coords[0])
                                    try:
                                        outer_polys.append(Polygon(coords))
                                    except Exception:
                                        continue
                        if outer_polys:
                            # Normalize MultiPolygon / multiple outer rings to the largest polygon component by area
                            geom_shape = max(outer_polys, key=lambda p: p.area)

                    if geom_shape is None:
                        invalid += 1
                        continue

                    # Validate geometry validity
                    if not geom_shape.is_valid:
                        invalid += 1
                        continue

                    # Filter Geographically: must intersect BMC ward boundaries
                    if not prepared_boundary.intersects(geom_shape):
                        skipped += 1
                        continue
                    
                    bmc_relevant += 1

                    # Parse attributes
                    building_type = tags.get("building", "yes")
                    if building_type:
                        building_type = str(building_type).strip()
                    
                    height = parse_height(tags.get("height"))
                    levels = parse_levels(tags.get("building:levels"))

                    # Perform Upsert
                    if osm_id in existing_map:
                        building = existing_map[osm_id]
                        building.building_type = building_type
                        building.height = height
                        building.levels = levels
                        building.geom = from_shape(geom_shape, srid=4326)
                        updated += 1
                    else:
                        new_building = Building(
                            osm_id=osm_id,
                            building_type=building_type,
                            height=height,
                            levels=levels,
                            geom=from_shape(geom_shape, srid=4326)
                        )
                        db.add(new_building)
                        inserted += 1

                except Exception as fe:
                    errors += 1
                    logger.error(f"Error processing OSM building element {osm_id}: {fe}")
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
    logger.info(f"BMC-relevant features: {bmc_relevant}")
    logger.info(f"Inserted: {inserted}")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Invalid: {invalid}")
    logger.info(f"Errors: {errors}")
    logger.info("Building ingestion completed.")

if __name__ == "__main__":
    raw_file = os.path.join(project_root, "data", "raw", "infrastructure", "bhubaneswar_buildings.json")
    ingest_buildings(raw_file)
