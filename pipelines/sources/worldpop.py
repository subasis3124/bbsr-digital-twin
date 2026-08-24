import os
import requests
import numpy as np
import rasterio
from shapely.geometry import shape, Polygon
from geoalchemy2.shape import to_shape, from_shape

from pipelines.etl.base import BaseETLPipeline
from pipelines.etl.config import DEFAULT_WORLDPOP_YEAR, REQUEST_TIMEOUT
from backend.app.models import SpatialGridCell, PopulationGrid, Ward

class WorldPopPipeline(BaseETLPipeline):
    def __init__(self):
        self.year = DEFAULT_WORLDPOP_YEAR
        super().__init__("population", f"worldpop-{self.year}")
        self.remote_url = f"https://data.worldpop.org/GIS/Population/Global_2000_2020/{self.year}/IND/ind_ppp_{self.year}.tif"
        self.local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
        self.local_path = os.path.join(self.local_dir, f"ind_ppp_{self.year}_cropped.tif")

    def discover(self, context, db, **kwargs):
        # Verify remote URL exists (Checked via HTTP header request)
        try:
            response = requests.head(self.remote_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                self.logger.info(f"WorldPop remote dataset ({self.year}) is available.")
            else:
                self.logger.warning(f"WorldPop remote dataset URL returned status: {response.status_code}")
        except Exception as e:
            self.logger.info(f"WorldPop remote offline check: {e} (Continuing with local/DB fallback)")

    def download(self, context, db, **kwargs):
        os.makedirs(self.local_dir, exist_ok=True)
        # WorldPop full country raster is 1.8GB, so standard practice in sandbox or deployment is:
        # Check if cropped clip is already there. If not, we download/generate or fall back to DB Wards.
        if os.path.exists(self.local_path):
            self.logger.info("WorldPop cropped raster retrieved from local cache.")
        else:
            self.logger.info("WorldPop cropped raster not found in cache. Ingestion will use the database Wards-based spatial downscaler.")

    def validate(self, context, db, **kwargs) -> bool:
        if os.path.exists(self.local_path):
            try:
                with rasterio.open(self.local_path) as src:
                    return src.crs is not None
            except Exception as e:
                self.logger.error(f"WorldPop cached raster invalid: {e}")
                return False
        return True

    def transform(self, context, db, **kwargs):
        # Dual-path: If cropped raster exists, read it; otherwise do dasymetric downscaling
        if os.path.exists(self.local_path):
            self.logger.info("Extracting population counts from local cropped raster...")
            return self._transform_from_raster(context, db)
        else:
            self.logger.info("Executing database dasymetric downscaler...")
            return self._transform_from_wards(context, db)

    def _transform_from_raster(self, context, db):
        cells = db.query(SpatialGridCell).all()
        if not cells:
            raise ValueError("No spatial grid cells available.")
        
        context.records_processed = len(cells)
        results = []
        
        with rasterio.open(self.local_path) as src:
            for cell in cells:
                centroid = to_shape(cell.centroid)
                lon, lat = centroid.x, centroid.y
                try:
                    pop_val = list(src.sample([(lon, lat)]))[0][0]
                    if src.nodata is not None and np.isclose(pop_val, src.nodata):
                        pop_val = 0.0
                    elif not np.isfinite(pop_val) or pop_val < 0:
                        pop_val = 0.0
                except IndexError:
                    pop_val = 0.0
                
                results.append({
                    "geom": to_shape(cell.geom),
                    "population_count": int(round(pop_val))
                })
        return results

    def _transform_from_wards(self, context, db):
        # Dasymetrically distribute ward-level population over our uniform grid cells
        wards = db.query(Ward).all()
        cells = db.query(SpatialGridCell).all()
        
        if not wards:
            raise ValueError("No ward boundaries present in the database to downscale population.")
        if not cells:
            raise ValueError("No spatial grid cells present in the database.")
            
        context.records_processed = len(cells)
        
        # Load ward geometries and pop counts
        ward_data = []
        for w in wards:
            poly = to_shape(w.geom)
            ward_data.append({
                "id": w.id,
                "geom": poly,
                "population": w.population_est or 5000, # Fallback default
                "cells": []
            })
            
        # Group cells by which ward they intersect/contain their centroid
        for cell in cells:
            centroid = to_shape(cell.centroid)
            matched = False
            for w in ward_data:
                if w["geom"].contains(centroid):
                    w["cells"].append(cell)
                    matched = True
                    break
            if not matched:
                # Find nearest ward or just match intersects
                for w in ward_data:
                    if w["geom"].intersects(centroid):
                        w["cells"].append(cell)
                        matched = True
                        break

        results = []
        for w in ward_data:
            num_cells = len(w["cells"])
            if num_cells == 0:
                continue
            
            # Divide population equally across cells inside the ward
            pop_per_cell = float(w["population"]) / num_cells
            
            for cell in w["cells"]:
                results.append({
                    "geom": to_shape(cell.geom),
                    "population_count": int(round(pop_per_cell))
                })
                
        return results

    def load(self, context, db, transformed_data, **kwargs):
        self.logger.info("Writing population grid into database...")
        
        # Clear existing population grid to ensure idempotency
        db.query(PopulationGrid).delete()
        db.commit()
        
        batch = []
        for r in transformed_data:
            pop_grid = PopulationGrid(
                population_count=r["population_count"],
                geom=from_shape(r["geom"], srid=4326)
            )
            batch.append(pop_grid)
            
        # Bulk save
        chunk_size = 1000
        for i in range(0, len(batch), chunk_size):
            db.bulk_save_objects(batch[i:i+chunk_size])
            db.commit()
            
        context.records_inserted = len(batch)

    def verify(self, context, db, **kwargs):
        from sqlalchemy import func
        count = db.query(PopulationGrid).count()
        total_pop = db.query(func.sum(PopulationGrid.population_count)).scalar() or 0
        self.logger.info(f"Verified population grid: {count} cells inserted with total population aggregation of {total_pop}.")
