from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from geoalchemy2.shape import from_shape
from backend.app.database import SessionLocal
from backend.app.models import Ward, SpatialGridCell
from pipelines.etl.logging import get_etl_logger
from pipelines.etl.config import BHUBANESWAR_BBOX

logger = get_etl_logger("ETL.GridInit")

def initialize_spatial_grid(cell_size_deg=0.0015):
    """
    Generates uniform grid cells over the union of 67 wards boundaries of Bhubaneswar.
    Saves cells in the spatial_grid_cells table.
    cell_size_deg=0.0015 is roughly 150m.
    """
    db = SessionLocal()
    try:
        # Check if grid already populated
        existing = db.query(SpatialGridCell).count()
        if existing > 0:
            logger.info(f"Spatial grid cell table already initialized with {existing} cells. Skipping.")
            return existing

        logger.info("Initializing spatial grid cells...")
        
        # 1. Load ward boundaries and shape their union
        wards = db.query(Ward).all()
        if not wards:
            logger.warning("No wards found in database. Initializing grid using the bounding box config.")
            bbox_poly = Polygon([
                (BHUBANESWAR_BBOX[0], BHUBANESWAR_BBOX[1]),
                (BHUBANESWAR_BBOX[0], BHUBANESWAR_BBOX[3]),
                (BHUBANESWAR_BBOX[2], BHUBANESWAR_BBOX[3]),
                (BHUBANESWAR_BBOX[2], BHUBANESWAR_BBOX[1]),
                (BHUBANESWAR_BBOX[0], BHUBANESWAR_BBOX[1])
            ])
            region_union = bbox_poly
            min_x, min_y, max_x, max_y = BHUBANESWAR_BBOX
        else:
            from geoalchemy2.shape import to_shape
            ward_shapes = [to_shape(w.geom) for w in wards]
            region_union = unary_union(ward_shapes)
            min_x, min_y, max_x, max_y = region_union.bounds

        logger.info(f"Region bounds: X=[{min_x:.4f}, {max_x:.4f}], Y=[{min_y:.4f}, {max_y:.4f}]")

        # 2. Iterate coordinate bounds and generate cells
        x_steps = int((max_x - min_x) / cell_size_deg) + 2
        y_steps = int((max_y - min_y) / cell_size_deg) + 2

        cells_to_insert = []
        cell_idx = 1
        
        for i in range(x_steps):
            for j in range(y_steps):
                x1 = min_x + i * cell_size_deg
                y1 = min_y + j * cell_size_deg
                x2 = x1 + cell_size_deg
                y2 = y1 + cell_size_deg

                cell_poly = Polygon([(x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)])
                
                # Check intersection with region boundary
                if region_union.intersects(cell_poly):
                    centroid = Point(x1 + cell_size_deg/2.0, y1 + cell_size_deg/2.0)
                    cell_code = f"BBSR-GRID-{cell_idx}"
                    
                    grid_cell = SpatialGridCell(
                        cell_code=cell_code,
                        geom=from_shape(cell_poly, srid=4326),
                        centroid=from_shape(centroid, srid=4326)
                    )
                    cells_to_insert.append(grid_cell)
                    cell_idx += 1

        logger.info(f"Generated {len(cells_to_insert)} grid cells intersecting with BMC territory. Inserting to DB...")
        
        # Insert in chunks of 1000
        chunk_size = 1000
        for offset in range(0, len(cells_to_insert), chunk_size):
            db.bulk_save_objects(cells_to_insert[offset:offset+chunk_size])
            db.commit()
            
        logger.info(f"Spatial grid initialization completed. Total cells: {len(cells_to_insert)}")
        return len(cells_to_insert)

    except Exception as e:
        db.rollback()
        logger.error(f"Error during spatial grid initialization: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    initialize_spatial_grid()
