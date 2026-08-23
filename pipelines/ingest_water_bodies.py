import os
import sys
import json
import logging
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.prepared import prep
from geoalchemy2.shape import from_shape, to_shape

# Setup path logic to import backend modules cleanly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.database import SessionLocal
from backend.app.models import Ward, WaterBody

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("water_bodies_ingestion")

def parse_geometry(elem):
    """
    Parses OSM geometry into a single Polygon geometry.
    For relations, resolves to the largest component Polygon by area.
    """
    elem_type = elem.get("type")
    if elem_type == "way":
        geometry_nodes = elem.get("geometry", [])
        if geometry_nodes and len(geometry_nodes) >= 3:
            coords = [(node["lon"], node["lat"]) for node in geometry_nodes]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            try:
                return Polygon(coords)
            except Exception:
                pass
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
            return max(outer_polys, key=lambda p: p.area)
    return None

def ingest_water_bodies(json_path: str):
    """
    Ingests water bodies from raw OSM JSON into the database.
    Performs boundary filtering, validation, polygon normalization, and idempotent bulk upsert.
    """
    logger.info("Water bodies ingestion started...")

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
    accepted = 0

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
            
            # Fetch existing water body osm_ids in the current batch
            osm_ids_in_batch = []
            for elem in batch_elements:
                osm_id = elem.get("id")
                if osm_id is not None:
                    osm_ids_in_batch.append(osm_id)
            
            existing_water_bodies = db.query(WaterBody).filter(WaterBody.osm_id.in_(osm_ids_in_batch)).all()
            existing_map = {int(wb.osm_id): wb for wb in existing_water_bodies}
            
            for elem in batch_elements:
                osm_id = elem.get("id")
                elem_type = elem.get("type")
                tags = elem.get("tags", {})
                name = tags.get("name")

                try:
                    if osm_id is None:
                        invalid += 1
                        continue

                    if name:
                        name = str(name).strip()
                    else:
                        name = None # Stored as NULL in database where allowed

                    geom_shape = parse_geometry(elem)

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

                    accepted += 1

                    # Parse attributes
                    water_type = tags.get("water") or tags.get("waterway") or tags.get("landuse") or tags.get("natural", "water")
                    if water_type:
                        water_type = str(water_type).strip()

                    # Perform Upsert
                    if osm_id in existing_map:
                        water_body = existing_map[osm_id]
                        water_body.name = name
                        water_body.water_type = water_type
                        water_body.geom = from_shape(geom_shape, srid=4326)
                        updated += 1
                    else:
                        new_water_body = WaterBody(
                            osm_id=osm_id,
                            name=name,
                            water_type=water_type,
                            geom=from_shape(geom_shape, srid=4326)
                        )
                        db.add(new_water_body)
                        inserted += 1

                except Exception as fe:
                    errors += 1
                    logger.error(f"Error processing OSM water body element {osm_id}: {fe}")
                    continue

        # Commit transaction
        db.commit()
        logger.info("Database transaction committed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Catastrophic error during ingestion transaction: {e}. Transaction rolled back.")
        raise e
    finally:
        db.close()

    # Log summary statistics
    logger.info(f"Accepted features: {accepted}")
    logger.info(f"Inserted: {inserted}")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Invalid: {invalid}")
    logger.info(f"Errors: {errors}")
    logger.info("Water bodies ingestion completed.")

if __name__ == "__main__":
    raw_file = os.path.join(project_root, "data", "raw", "infrastructure", "bhubaneswar_water_bodies.json")
    ingest_water_bodies(raw_file)
