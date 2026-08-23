import os
import sys
import json
import logging
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, linemerge
from shapely.prepared import prep
from geoalchemy2.shape import from_shape, to_shape

# Setup path logic to import backend modules cleanly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.database import SessionLocal
from backend.app.models import Ward, BusRoute

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bus_routes_ingestion")

def parse_geometry(elem):
    """
    Parses OSM relation type=route route=bus geometry into a single LineString geometry.
    Merges members of type'way' into a single continuous LineString.
    If linemerge results in a MultiLineString, returns the longest component LineString.
    If linemerge fails, chains the coordinates in order of constituent ways.
    """
    elem_type = elem.get("type")
    if elem_type != "relation":
        return None

    members = elem.get("members", [])
    lines = []
    
    for member in members:
        if member.get("type") == "way":
            geometry_nodes = member.get("geometry", [])
            if geometry_nodes and len(geometry_nodes) >= 2:
                coords = [(n["lon"], n["lat"]) for n in geometry_nodes]
                try:
                    lines.append(LineString(coords))
                except Exception:
                    continue

    if not lines:
        return None

    try:
        # Attempt to merge multiple linestrings into one continuous string
        merged = linemerge(lines)
        if isinstance(merged, LineString):
            return merged
        elif isinstance(merged, MultiLineString):
            if not merged.is_empty:
                # Return the longest LineString component to conform with table's LINESTRING structure
                return max(merged.geoms, key=lambda l: l.length)
    except Exception:
        pass

    # Fallback: chain all points directly
    fallback_coords = []
    for line in lines:
        for pt in line.coords:
            if not fallback_coords or fallback_coords[-1] != pt:
                fallback_coords.append(pt)
    if len(fallback_coords) >= 2:
        try:
            return LineString(fallback_coords)
        except Exception:
            pass

    return None

def ingest_bus_routes(json_path: str):
    """
    Ingests bus routes from raw OSM JSON into the database.
    Performs boundary filtering (BMC wards), geometry reconstruction, and idempotent upserts.
    """
    logger.info("Bus routes ingestion started...")

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

        # Query all existing bus routes to construct an idempotency map matching route_name
        existing_routes = db.query(BusRoute).all()
        existing_map = {br.route_name.strip(): br for br in existing_routes if br.route_name}

        for elem in elements:
            osm_id = elem.get("id")
            tags = elem.get("tags", {})
            
            # Extract names & fallbacks
            name = tags.get("name") or tags.get("ref") or f"Bus Route {osm_id}"
            name = str(name).strip()
            
            operator = tags.get("operator") or "CRUT"
            operator = str(operator).strip()

            try:
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

                # Perform idempotent upsert on route_name
                if name in existing_map:
                    bus_route = existing_map[name]
                    bus_route.operator = operator
                    bus_route.geom = from_shape(geom_shape, srid=4326)
                    updated += 1
                else:
                    new_bus_route = BusRoute(
                        route_name=name,
                        operator=operator,
                        geom=from_shape(geom_shape, srid=4326)
                    )
                    db.add(new_bus_route)
                    # Add to local map to prevent duplicates within the same batch
                    existing_map[name] = new_bus_route
                    inserted += 1

            except Exception as fe:
                errors += 1
                logger.error(f"Error processing OSM bus route element {osm_id}: {fe}")
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
    logger.info("Bus routes ingestion completed.")

if __name__ == "__main__":
    raw_file = os.path.join(project_root, "data", "raw", "infrastructure", "bhubaneswar_bus_routes.json")
    ingest_bus_routes(raw_file)
