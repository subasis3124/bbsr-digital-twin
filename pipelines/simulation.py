import argparse
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from backend.app.database import SessionLocal
from backend.app import models
from ml.simulation import WhatIfSimulationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipelines.simulation")

def run_simulation_pipeline(
    scenario_type: str = "heavy_rainfall",
    parameters: Optional[Dict[str, Any]] = None,
    base_timestamp_str: Optional[str] = None,
    simulation_timestamp_str: Optional[str] = None,
    spatial_scope: Optional[Dict[str, Any]] = None,
    limit: int = 20,
    save: bool = True,
    dry_run: bool = False,
    output_file: Optional[str] = None,
    db_session: Any = None
) -> Dict[str, Any]:
    """
    CLI Pipeline runner for executing, validating, and recording What-If Simulation Scenarios.
    """
    logger.info(f"Starting What-If Simulation Pipeline: scenario='{scenario_type}'...")

    ts_base = None
    if base_timestamp_str:
        try:
            ts_base = datetime.fromisoformat(base_timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid base timestamp format '{base_timestamp_str}'. Expected ISO 8601.")
            if db_session is None:
                sys.exit(1)
            raise

    ts_sim = None
    if simulation_timestamp_str:
        try:
            ts_sim = datetime.fromisoformat(simulation_timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid simulation timestamp format '{simulation_timestamp_str}'. Expected ISO 8601.")
            if db_session is None:
                sys.exit(1)
            raise

    if parameters is None:
        if scenario_type == "heavy_rainfall":
            parameters = {"rainfall_multiplier": 1.5, "rainfall_delta_mm": 25.0}
        elif scenario_type == "road_closure":
            parameters = {"closed_road_ids": [101]}
        elif scenario_type == "air_pollution":
            parameters = {"pollutant": "pm25", "multiplier": 2.0}
        elif scenario_type == "emergency_demand":
            parameters = {"hospital_demand_multiplier": 1.5}

    db_created = False
    if db_session is None:
        db = SessionLocal()
        db_created = True
    else:
        db = db_session

    try:
        engine = WhatIfSimulationEngine(db=db)
        should_save = save and not dry_run

        result = engine.run_simulation(
            scenario_type=scenario_type,
            parameters=parameters,
            base_timestamp=ts_base,
            simulation_timestamp=ts_sim,
            spatial_scope=spatial_scope,
            save=should_save
        )

        res_dict = result.model_dump()
        logger.info(
            f"Simulation executed successfully! ID: {result.scenario.scenario_id}, "
            f"Impact Severity: {result.impact_summary.overall_severity}, "
            f"Affected Units: {result.impact_summary.affected_spatial_units_count}"
        )

        if output_file:
            with open(output_file, "w") as f:
                json.dump(res_dict, f, indent=2)
            logger.info(f"Saved simulation results to {output_file}")

        return res_dict
    finally:
        if db_created:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BBSR Digital Twin What-If Simulation Engine Runner")
    parser.add_argument("--scenario-type", "-s", type=str, default="heavy_rainfall", choices=["heavy_rainfall", "road_closure", "air_pollution", "emergency_demand"])
    parser.add_argument("--parameters", "-p", type=str, default=None, help="JSON string of scenario parameters")
    parser.add_argument("--base-timestamp", type=str, default=None, help="Base state ISO 8601 timestamp")
    parser.add_argument("--simulation-timestamp", type=str, default=None, help="Simulation target ISO 8601 timestamp")
    parser.add_argument("--limit", "-l", type=int, default=20, help="Limit base spatial units")
    parser.add_argument("--no-save", action="store_true", help="Do not save simulation run to database")
    parser.add_argument("--dry-run", action="store_true", help="Execute without side-effects")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output JSON filepath")

    args = parser.parse_args()

    parsed_params = None
    if args.parameters:
        try:
            parsed_params = json.loads(args.parameters)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse --parameters JSON: {e}")
            sys.exit(1)

    run_simulation_pipeline(
        scenario_type=args.scenario_type,
        parameters=parsed_params,
        base_timestamp_str=args.base_timestamp,
        simulation_timestamp_str=args.simulation_timestamp,
        limit=args.limit,
        save=not args.no_save,
        dry_run=args.dry_run,
        output_file=args.output
    )
