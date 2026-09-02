import argparse
import sys
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from backend.app.database import SessionLocal
from backend.app import models
from ml.city_state import CityStateAggregator, CityStateValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipelines.city_state")

def run_city_state_pipeline(
    timestamp_str: str = None,
    forecast_horizon_minutes: int = 0,
    spatial_unit: str = "grid_cell",
    limit: int = 50,
    save: bool = True,
    dry_run: bool = False,
    strict_validate: bool = True,
    db_session: Any = None
):
    """
    CLI Pipeline for generating, validating, and persisting City State snapshots.
    """
    logger.info("Starting Unified City State Generation Pipeline...")

    ts_target = None
    if timestamp_str:
        try:
            ts_target = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid timestamp format '{timestamp_str}'. Expected ISO 8601 string.")
            sys.exit(1)

    db_created = False
    if db_session is None:
        db = SessionLocal()
        db_created = True
    else:
        db = db_session
    try:
        aggregator = CityStateAggregator(db)
        processed_count = 0
        validation_errors_count = 0
        snapshots_saved = 0

        if spatial_unit in ["grid_cell", "all"]:
            grid_cells = db.query(models.SpatialGridCell).limit(limit).all()
            logger.info(f"Processing {len(grid_cells)} SpatialGridCells...")

            for cell in grid_cells:
                c_state = aggregator.aggregate_grid_cell(
                    cell,
                    state_timestamp=ts_target,
                    forecast_horizon_minutes=forecast_horizon_minutes
                )

                if strict_validate:
                    val_res = CityStateValidator.validate(c_state)
                    if not val_res.is_valid:
                        validation_errors_count += 1
                        logger.warning(f"Validation failure for cell {cell.cell_code}: {val_res.errors}")

                if save and not dry_run:
                    aggregator.save_snapshot(c_state)
                    snapshots_saved += 1

                processed_count += 1

        if spatial_unit in ["ward", "all"]:
            wards = db.query(models.Ward).limit(limit).all()
            logger.info(f"Processing {len(wards)} Wards...")

            for ward in wards:
                c_state = aggregator.aggregate_ward(
                    ward,
                    state_timestamp=ts_target,
                    forecast_horizon_minutes=forecast_horizon_minutes
                )

                if strict_validate:
                    val_res = CityStateValidator.validate(c_state)
                    if not val_res.is_valid:
                        validation_errors_count += 1
                        logger.warning(f"Validation failure for ward {ward.ward_number}: {val_res.errors}")

                if save and not dry_run:
                    aggregator.save_snapshot(c_state)
                    snapshots_saved += 1

                processed_count += 1

        logger.info(
            f"Pipeline Execution Complete. Processed: {processed_count}, "
            f"Validation Failures: {validation_errors_count}, Snapshots Saved: {snapshots_saved}"
        )
        return {
            "processed_count": processed_count,
            "validation_failures": validation_errors_count,
            "snapshots_saved": snapshots_saved
        }
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin Unified City State Generator")
    parser.add_argument("--timestamp", "-t", type=str, default=None, help="Target ISO 8601 timestamp")
    parser.add_argument("--forecast-horizon", "-f", type=int, default=0, help="Forecast horizon in minutes")
    parser.add_argument("--spatial-unit", "-s", type=str, default="grid_cell", choices=["grid_cell", "ward", "all"])
    parser.add_argument("--limit", "-l", type=int, default=50, help="Limit number of spatial units to process")
    parser.add_argument("--no-save", action="store_true", help="Do not persist snapshots to database")
    parser.add_argument("--dry-run", action="store_true", help="Compute and validate without database side-effects")
    parser.add_argument("--skip-validation", action="store_true", help="Skip strict validation checks")

    args = parser.parse_args()
    run_city_state_pipeline(
        timestamp_str=args.timestamp,
        forecast_horizon_minutes=args.forecast_horizon,
        spatial_unit=args.spatial_unit,
        limit=args.limit,
        save=not args.no_save,
        dry_run=args.dry_run,
        strict_validate=not args.skip_validation
    )
