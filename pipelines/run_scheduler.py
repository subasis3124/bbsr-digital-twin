import time
import os
import sys
from datetime import datetime, timedelta, timezone

from pipelines.sources.copernicus_dem import CopernicusDEMPipeline
from pipelines.sources.worldpop import WorldPopPipeline
from pipelines.sources.sentinel2 import Sentinel2Pipeline
from pipelines.sources.open_meteo import OpenMeteoPipeline
from pipelines.sources.air_quality import AirQualityPipeline
from pipelines.etl.logging import get_etl_logger
from pipelines.etl.initialize_grid import initialize_spatial_grid

logger = get_etl_logger("ETL.Scheduler")

# Import pipelines config mapping
PIPELINES_MAP = {
    "dem": CopernicusDEMPipeline,
    "population": WorldPopPipeline,
    "sentinel2": Sentinel2Pipeline,
    "weather": OpenMeteoPipeline,
    "air_quality": AirQualityPipeline
}

# Configurable intervals in seconds (defaults)
# These can be configured in .env
DEFAULT_INTERVALS = {
    "air_quality": int(os.getenv("SCHEDULE_INTERVAL_AQ", "900")),      # 15 minutes
    "weather": int(os.getenv("SCHEDULE_INTERVAL_WEATHER", "3600")),     # 1 hour
    "sentinel2": int(os.getenv("SCHEDULE_INTERVAL_S2", "86400")),       # 1 day
    "dem": int(os.getenv("SCHEDULE_INTERVAL_DEM", "604800")),           # 1 week
    "population": int(os.getenv("SCHEDULE_INTERVAL_POP", "2592000"))     # 30 days
}

def run_job(source):
    logger.info(f"Scheduled Trigger: Starting {source} pipeline...")
    try:
        pipeline_class = PIPELINES_MAP[source]
        pipeline = pipeline_class()
        pipeline.run()
        logger.info(f"Scheduled Trigger: {source} pipeline finished successfully.")
        return True
    except Exception as e:
        logger.error(f"Scheduled Trigger: {source} pipeline failed: {e}")
        return False

def main():
    logger.info("Initializing BBSR Digital Twin ETL Scheduler...")
    
    # 1. Proactively initialize the geographical grid
    try:
        initialize_spatial_grid()
    except Exception as e:
        logger.critical(f"Failed to initialize base spatial grid cells: {e}. Exiting.")
        sys.exit(1)

    # Dictionary to keep track of last run timestamps
    last_runs = {source: None for source in PIPELINES_MAP.keys()}
    
    # Optional backfill on startup option
    run_on_startup = os.getenv("ETL_RUN_ON_STARTUP", "true").lower() == "true"
    if run_on_startup:
        logger.info("Running initial backfill of all pipelines on startup...")
        # Order matters! Populate static terrain and grids first, then dynamic observations
        startup_queue = ["dem", "population", "sentinel2", "weather", "air_quality"]
        for source in startup_queue:
            run_job(source)
            last_runs[source] = datetime.now(timezone.utc)
            
    logger.info("Scheduler is now running. Monitoring intervals...")
    for src, sec in DEFAULT_INTERVALS.items():
        logger.info(f" - {src}: configured to run every {sec} seconds ({timedelta(seconds=sec)})")

    # Daemon loop
    try:
        while True:
            now = datetime.now(timezone.utc)
            for source, interval_sec in DEFAULT_INTERVALS.items():
                last_run = last_runs[source]
                
                # Check if it has never run or if the interval has elapsed
                if last_run is None or (now - last_run).total_seconds() >= interval_sec:
                    run_job(source)
                    last_runs[source] = datetime.now(timezone.utc)
                    
            # Sleep for 10 seconds before next check
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by keyboard interrupt.")
        sys.exit(0)

if __name__ == "__main__":
    main()
