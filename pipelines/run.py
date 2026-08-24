import argparse
import sys
from pipelines.sources.copernicus_dem import CopernicusDEMPipeline
from pipelines.sources.worldpop import WorldPopPipeline
from pipelines.sources.sentinel2 import Sentinel2Pipeline
from pipelines.sources.open_meteo import OpenMeteoPipeline
from pipelines.sources.air_quality import AirQualityPipeline
from pipelines.sources.flood_target import FloodTargetPipeline
from pipelines.etl.logging import get_etl_logger
from pipelines.etl.initialize_grid import initialize_spatial_grid

logger = get_etl_logger("ETL.CLI")

PIPELINES_MAP = {
    "dem": CopernicusDEMPipeline,
    "population": WorldPopPipeline,
    "sentinel2": Sentinel2Pipeline,
    "weather": OpenMeteoPipeline,
    "air_quality": AirQualityPipeline,
    "flood_target": FloodTargetPipeline
}

def main():
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - Reusable ETL Framework CLI")
    parser.add_argument(
        "--source",
        choices=list(PIPELINES_MAP.keys()) + ["all"],
        required=True,
        help="Specify which pipeline/source to run, or run 'all' sequentially."
    )
    parser.add_argument(
        "--init-grid",
        action="store_true",
        help="Initialize/seed the spatial grid cells table if not already populated."
    )
    
    args = parser.parse_args()
    
    # 1. Optionally initialize grid
    if args.init_grid:
        logger.info("Initializing spatial grid cells table...")
        initialize_spatial_grid()
        
    # 2. Run target pipelines
    sources_to_run = []
    if args.source == "all":
        # Order matters! Grid, DEM, and Sentinel2 rely on grid cells. DEM/Sentinel2 prepare land cover features.
        sources_to_run = ["dem", "population", "sentinel2", "weather", "air_quality"]
    else:
        sources_to_run = [args.source]
        
    logger.info(f"Triggering ETL pipelines for: {sources_to_run}")
    
    success_count = 0
    failure_count = 0
    
    for source in sources_to_run:
        logger.info(f"Executing {source} pipeline...")
        try:
            pipeline_class = PIPELINES_MAP[source]
            pipeline = pipeline_class()
            pipeline.run()
            success_count += 1
            logger.info(f"Pipeline {source} finished successfully.")
        except Exception as e:
            failure_count += 1
            logger.error(f"Pipeline {source} execution failed: {e}")
            
    logger.info(f"ETL run finished. Completed: {success_count}, Failed: {failure_count}")
    
    if failure_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
