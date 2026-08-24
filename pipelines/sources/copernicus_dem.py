import os
import requests
import numpy as np
import rasterio
from datetime import datetime, timezone
from shapely.geometry import Point
from geoalchemy2.shape import to_shape

from pipelines.etl.base import BaseETLPipeline
from pipelines.etl.config import REQUEST_TIMEOUT, MAX_RETRIES, BACKOFF_FACTOR
from pipelines.etl.retry import retry_operation
from backend.app.models import SpatialGridCell, SatelliteFeature

class CopernicusDEMPipeline(BaseETLPipeline):
    def __init__(self):
        super().__init__("dem", "copernicus-glo30")
        self.tile_url = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N20_00_E085_00_DEM/Copernicus_DSM_COG_10_N20_00_E085_00_DEM.tif"
        self.local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
        self.local_path = os.path.join(self.local_dir, "copernicus_dem_N20_E085.tif")

    def discover(self, context, db, **kwargs):
        # Determine if remote URL is available (checked via headers)
        response = requests.head(self.tile_url, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            raise ConnectionError(f"Copernicus GLO-30 DEM tile URL is not accessible: Status {response.status_code}")
        self.logger.info("Copernicus DEM remote tile is discoverable.")

    def download(self, context, db, **kwargs):
        os.makedirs(self.local_dir, exist_ok=True)
        if os.path.exists(self.local_path):
            self.logger.info("Copernicus DEM tile already exists in local cache. Skipping download.")
            return

        self.logger.info(f"Downloading Copernicus DEM tile from {self.tile_url}...")
        response = requests.get(self.tile_url, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        with open(self.local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        self.logger.info("Download completed and cached.")

    def validate(self, context, db, **kwargs) -> bool:
        if not os.path.exists(self.local_path):
            return False
        
        try:
            with rasterio.open(self.local_path) as src:
                self.logger.info(f"DEM Metadata: CRS={src.crs}, Dimensions={src.width}x{src.height}, Bounds={src.bounds}")
                # Ensure CRS is geographic or projected
                if not src.crs:
                    self.logger.error("DEM raster does not have a valid CRS.")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"DEM raster validation failed: {e}")
            return False

    def transform(self, context, db, **kwargs):
        self.logger.info("Sampling elevation and calculating slope for all grid cells...")
        
        # Load all spatial grid cells
        cells = db.query(SpatialGridCell).all()
        if not cells:
            raise ValueError("No spatial grid cells found in database. Run initialize_grid first.")
        
        context.records_processed = len(cells)
        results = []
        static_timestamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Open raster for sampling
        with rasterio.open(self.local_path) as src:
            for cell in cells:
                centroid = to_shape(cell.centroid)
                lon, lat = centroid.x, centroid.y
                
                # Sample center elevation
                try:
                    elev_val = list(src.sample([(lon, lat)]))[0][0]
                    # Check for nodata
                    if src.nodata is not None and np.isclose(elev_val, src.nodata):
                        elev_val = 0.0
                    elif not np.isfinite(elev_val):
                        elev_val = 0.0
                except IndexError:
                    elev_val = 0.0
                
                # Calculate slope at (lon, lat) using 4-way finite differences (dx/dy = 30m ~ 0.0003 deg)
                # At Lat 20 deg, 1 deg Lon is approx 104500m, 1 deg Lat is approx 110600m.
                # 0.0003 degrees in Lon is ~31.3m, in Lat is ~33.2m
                deg_offset = 0.0003
                dx_meters = deg_offset * 104500.0
                dy_meters = deg_offset * 110600.0
                
                try:
                    elev_e = list(src.sample([(lon + deg_offset, lat)]))[0][0]
                    elev_w = list(src.sample([(lon - deg_offset, lat)]))[0][0]
                    elev_n = list(src.sample([(lon, lat + deg_offset)]))[0][0]
                    elev_s = list(src.sample([(lon, lat - deg_offset)]))[0][0]
                    
                    # Nodata controls
                    for val in [elev_e, elev_w, elev_n, elev_s]:
                        if src.nodata is not None and np.isclose(val, src.nodata):
                            val = elev_val
                    
                    dz_dx = (elev_e - elev_w) / (2.0 * dx_meters)
                    dz_dy = (elev_n - elev_s) / (2.0 * dy_meters)
                    
                    slope_percent = np.sqrt(dz_dx**2 + dz_dy**2)
                    slope_deg = np.arctan(slope_percent) * 180.0 / np.pi
                    if not np.isfinite(slope_deg):
                        slope_deg = 0.0
                except IndexError:
                    slope_deg = 0.0
                
                results.append({
                    "cell_id": cell.id,
                    "timestamp": static_timestamp,
                    "elevation": float(elev_val),
                    "slope": float(slope_deg)
                })
                
        return results

    def load(self, context, db, transformed_data, **kwargs):
        self.logger.info("Upserting elevation and slope records into satellite_features...")
        
        inserted = 0
        updated = 0
        
        # Batch query existing to make it fast
        existing_records = db.query(SatelliteFeature).filter(
            SatelliteFeature.timestamp == transformed_data[0]["timestamp"]
        ).all()
        
        # Create mapping of cell_id -> record
        existing_map = {r.cell_id: r for r in existing_records}
        
        for record_dict in transformed_data:
            cell_id = record_dict["cell_id"]
            if cell_id in existing_map:
                # Update
                record = existing_map[cell_id]
                record.elevation = record_dict["elevation"]
                record.slope = record_dict["slope"]
                updated += 1
            else:
                # Insert
                record = SatelliteFeature(
                    cell_id=cell_id,
                    timestamp=record_dict["timestamp"],
                    elevation=record_dict["elevation"],
                    slope=record_dict["slope"]
                )
                db.add(record)
                inserted += 1
                
        db.commit()
        context.records_inserted = inserted
        context.records_updated = updated
        
    def verify(self, context, db, **kwargs):
        # Verify database state by matching row counts
        count = db.query(SatelliteFeature).filter(
            SatelliteFeature.elevation.isnot(None)
        ).count()
        self.logger.info(f"Verified {count} records in satellite_features have elevation attributes.")
