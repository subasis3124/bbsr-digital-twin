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
from backend.app.models import Ward, FireStation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("fire_ingestion")

def parse_geometry(elem):
    """
    Parses OSM geometry into a single Point geometry.
    If the feature is a Polygon (way) or MultiPolygon (relation), computes its centroid.
    """
    elem_type = elem.get("type")
    if elem_type == "node":
        lat = elem.get("lat")
        lon = elem.get("lon")
        if lat is not None and lon is not None:
            return Point(lon, lat)
    elif elem_type == "way":
        nodes = elem.get("geometry", [])
        if nodes and len(nodes) >= 3:
            coords = [(n["lon"], n["lat"]) for n in nodes]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            try:
                poly = Polygon(coords)
                return poly.centroid
            except Exception:
                return None
    elif elem_type == "relation":
        members = elem.get("members", [])
        outer_polys = []
        for m in members:
            if m.get("role") == "outer":
                nodes = m.get("geometry", [])
                if nodes and len(nodes) >= 3:
                    coords = [(n["lon"], n["lat"]) for n in nodes]
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    try:
                        outer_polys.append(Polygon(coords))
                    except Exception:
                        continue
        if outer_polys:
            largest_poly = max(outer_polys, key=lambda p: p.area)
            return largest_poly.centroid
    return None

def ingest_fire_stations(json_path: str):
    """
    Ingests fire stations from raw OSM JSON into the database.
    Performs boundary filtering, validation, centroid normalization, and idempotent bulk upsert.
    """
    logger.info("Fire station ingestion started...")

    if not os.path.exists(json_path):
        logger.error(f"Source JSON file not found at: {json_path}")
        sys.exit(1)

    logger.info(f"Opening OSM raw file: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    fire_elements = [elem for elem in elements if elem.get("tags", {}).get("amenity") == "fire_station"]
    total_elements = len(fire_elements)
    logger.info(f"Raw features matching amenity=fire_station: {total_elements}")

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

        # Query all existing fire station osm_ids
        existing_fire = db.query(FireStation).all()
        existing_map = {int(f.osm_id): f for f in existing_fire if f.osm_id is not None}

        for elem in fire_elements:
            osm_id = elem.get("id")
            tags = elem.get("tags", {})
            name = tags.get("name")

            try:
                if osm_id is None:
                    invalid += 1
                    continue

                # The name column is NOT NULL in database schema, so name is required
                if not name or not str(name).strip():
                    invalid += 1
                    continue
                name = str(name).strip()

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

                # Perform Upsert
                if osm_id in existing_map:
                    fire_station = existing_map[osm_id]
                    fire_station.name = name
                    fire_station.geom = from_shape(geom_shape, srid=4326)
                    updated += 1
                else:
                    new_fire = FireStation(
                        osm_id=osm_id,
                        name=name,
                        geom=from_shape(geom_shape, srid=4326)
                    )
                    db.add(new_fire)
                    inserted += 1

            except Exception as fe:
                errors += 1
                logger.error(f"Error processing OSM fire station element {osm_id}: {fe}")
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
    logger.info("Fire station ingestion completed.")

if __name__ == "__main__":
    raw_file = os.path.join(project_root, "data", "raw", "infrastructure", "bhubaneswar_safety.json")
    ingest_fire_stations(raw_file)
