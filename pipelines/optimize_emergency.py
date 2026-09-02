import argparse
import json
import sys
from datetime import datetime, timezone

from backend.app.database import SessionLocal
from ml.optimization import (
    EmergencyOptimizationEngine, OptimizationConstraints,
    EmergencyDemand, EmergencyResource
)


def run_cli():
    parser = argparse.ArgumentParser(description="BBSR Digital Twin - Emergency Resource Optimization CLI")
    parser.add_argument("--base-timestamp", type=str, default=None, help="Baseline state ISO timestamp")
    parser.add_argument("--simulation-id", type=str, default=None, help="Optional SimulationRun UUID for What-If scenario optimization")
    parser.add_argument("--resource-type", type=str, default="hospital", help="Target resource type: hospital, police_station, fire_station")
    parser.add_argument("--method", type=str, default="ortools_min_cost_flow", help="Optimization method: ortools_min_cost_flow or nearest_resource")
    parser.add_argument("--max-travel-cost", type=float, default=None, help="Maximum allowed travel cost (km)")
    parser.add_argument("--save", action="store_true", help="Persist optimization run results to database")
    parser.add_argument("--dry-run", action="store_true", help="Run optimization without database persistence")

    args = parser.parse_args()

    print("==================================================")
    print("BBSR DIGITAL TWIN — EMERGENCY RESOURCE OPTIMIZATION")
    print("==================================================")
    print(f"Timestamp: {args.base_timestamp or 'Current UTC'}")
    print(f"Simulation ID: {args.simulation_id or 'None (Base State Optimization)'}")
    print(f"Resource Type: {args.resource_type}")
    print(f"Method: {args.method}")
    print(f"Save to DB: {args.save and not args.dry_run}")
    print("--------------------------------------------------")

    db = None
    try:
        db = SessionLocal()
        # Test query to check if DB is reachable
        db.execute(SessionLocal().bind.text("SELECT 1") if hasattr(SessionLocal().bind, "text") else "SELECT 1")
    except Exception:
        db = None

    try:
        engine = EmergencyOptimizationEngine(db=db)
        ts_base = datetime.fromisoformat(args.base_timestamp.replace("Z", "+00:00")) if args.base_timestamp else None
        
        constraints = OptimizationConstraints(
            capacity_constrained=True,
            accessibility_constrained=True,
            max_travel_cost=args.max_travel_cost,
            priority_weighting=True
        )

        result = engine.optimize(
            base_timestamp=ts_base,
            simulation_id=args.simulation_id,
            resource_types=[args.resource_type],
            constraints=constraints,
            method=args.method,
            save=args.save and not args.dry_run and db is not None
        )

        print("\nOPTIMIZATION SUMMARY:")
        print(f"Total Demand Quantity: {result.summary.total_demand}")
        print(f"Served Demand:        {result.summary.served_demand}")
        print(f"Unserved Demand:      {result.summary.unserved_demand}")
        print(f"Total Travel Cost:    {result.summary.total_travel_cost:.2f} km")
        print(f"Average Travel Cost:  {result.summary.average_travel_cost:.2f} km")
        print(f"Max Travel Cost:      {result.summary.max_travel_cost:.2f} km")

        print("\nBASELINE COMPARISON (Nearest Resource):")
        print(f"Baseline Method:      {result.baseline_comparison.baseline_method}")
        print(f"Travel Cost Diff:     {result.baseline_comparison.total_travel_cost_diff:+.2f} km")
        print(f"Improvement:          {result.baseline_comparison.improvement_percentage:+.2f}%")
        print(f"Summary:              {result.baseline_comparison.comparison_summary}")

        if result.allocation_delta:
            print("\nWHAT-IF SIMULATION ALLOCATION DELTA:")
            print(result.allocation_delta.get("summary_text"))

        print("\nPROVENANCE:")
        print(f"Run ID:        {result.run_id}")
        print(f"Engine Ver:    {result.engine_version}")
        print(f"Is Synthetic:  {result.provenance.get('is_synthetic')}")

        print("\n[COMPLETE] Optimization completed successfully.")

    except Exception as err:
        print(f"\n[ERROR] Optimization failed: {str(err)}", file=sys.stderr)
        sys.exit(1)
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    run_cli()
