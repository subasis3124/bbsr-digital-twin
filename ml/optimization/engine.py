from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid
import json
import copy
from sqlalchemy.orm import Session

from backend.app import models
from ml.optimization.schemas import (
    EmergencyDemand, EmergencyResource, DemandAssignment,
    OptimizationConstraints, OptimizationRequest, OptimizationResult,
    OptimizationSummary, BaselineComparison
)
from ml.optimization.resources import EmergencyResourceExtractor
from ml.optimization.demand import EmergencyDemandGenerator
from ml.optimization.solver import ORToolsEmergencySolver
from ml.optimization.baseline import NearestAvailableResourceBaseline
from ml.optimization.explanation import OptimizationExplanationBuilder

DECISION_SUPPORT_WARNING = (
    "NOTICE: This is a model-based decision-support optimization tool. "
    "All allocations are scenario estimates intended for emergency planning and must be verified by operational command."
)


class EmergencyOptimizationEngine:
    """
    Unified Emergency Resource Optimization Engine.
    Executes min-cost flow & capacitated facility assignment on base or simulated city states.
    Produces deterministic, explainable, and benchmarked optimal allocations.
    """

    ENGINE_VERSION = "1.0.0"

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def optimize(
        self,
        base_timestamp: Optional[datetime] = None,
        simulation_id: Optional[str] = None,
        resource_types: Optional[List[str]] = None,
        demands: Optional[List[EmergencyDemand]] = None,
        resources: Optional[List[EmergencyResource]] = None,
        constraints: Optional[OptimizationConstraints] = None,
        method: str = "ortools_min_cost_flow",
        save: bool = False
    ) -> OptimizationResult:
        """
        Executes emergency resource optimization under base or simulated city states.
        """
        now_utc = datetime.now(timezone.utc)
        ts_base = base_timestamp or now_utc
        res_types = resource_types or ["hospital"]

        if not constraints:
            constraints = OptimizationConstraints()

        sim_run_record = None
        allocation_delta = None

        # 1. Handle Simulation Run Integration if simulation_id provided
        if simulation_id and self.db:
            sim_run_record = self.db.query(models.SimulationRun).filter(models.SimulationRun.simulation_id == simulation_id).first()
            if not sim_run_record:
                raise ValueError(f"SimulationRun with simulation_id '{simulation_id}' not found.")

        # 2. Extract or resolve Emergency Resources
        if not resources:
            if self.db:
                resources = EmergencyResourceExtractor.extract_from_db(self.db, resource_types=res_types, timestamp=ts_base)
            else:
                # Fallback synthetic resources for testing without DB
                resources = [
                    EmergencyResource(
                        resource_id="HOSP_001",
                        resource_type="hospital",
                        name="Capital Hospital Bhubaneswar",
                        coordinates=[85.8246, 20.2700],
                        capacity=50,
                        capacity_status="known",
                        available_capacity=50,
                        accessibility=1.0,
                        status="AVAILABLE",
                        timestamp=ts_base.isoformat()
                    ),
                    EmergencyResource(
                        resource_id="HOSP_002",
                        resource_type="hospital",
                        name="AIIMS Bhubaneswar",
                        coordinates=[85.8100, 20.2450],
                        capacity=40,
                        capacity_status="known",
                        available_capacity=40,
                        accessibility=1.0,
                        status="AVAILABLE",
                        timestamp=ts_base.isoformat()
                    )
                ]

        # If simulation record exists, update resource accessibility if affected by scenario
        if sim_run_record and sim_run_record.scenario_type == "road_closure":
            params = sim_run_record.parameters or {}
            closed_ids = params.get("closed_road_ids", [])
            # Mark matching resources or affected roads as degraded/inaccessible
            for r in resources:
                if any(str(cid) in r.name or str(cid) in r.resource_id for cid in closed_ids):
                    r.accessibility = 0.0
                    r.status = "INACCESSIBLE"

        # 3. Extract or resolve Emergency Demands
        if not demands:
            if self.db:
                demands = EmergencyDemandGenerator.generate_from_wards(self.db, timestamp=ts_base)
            else:
                # Fallback synthetic demands for testing without DB
                demands = [
                    EmergencyDemand(
                        demand_id="DEMAND_001",
                        spatial_id="WARD_01",
                        coordinates=[85.8300, 20.2750],
                        timestamp=ts_base.isoformat(),
                        demand_quantity=15,
                        emergency_type="medical",
                        priority="HIGH",
                        priority_weight=1.5
                    ),
                    EmergencyDemand(
                        demand_id="DEMAND_002",
                        spatial_id="WARD_02",
                        coordinates=[85.8150, 20.2500],
                        timestamp=ts_base.isoformat(),
                        demand_quantity=25,
                        emergency_type="medical",
                        priority="CRITICAL",
                        priority_weight=3.0
                    )
                ]

        # 4. Run Primary OR-Tools Optimization Solver
        if method == "nearest_resource":
            opt_allocations, opt_summary = NearestAvailableResourceBaseline.solve(demands, resources)
            opt_method_name = "NEAREST_AVAILABLE_RESOURCE"
        else:
            opt_allocations, opt_summary = ORToolsEmergencySolver.solve(demands, resources, constraints)
            opt_method_name = "OR-Tools Min-Cost Flow (CBC)"

        # 5. Run Baseline Heuristic Solver for Comparison
        base_allocations, base_summary = NearestAvailableResourceBaseline.solve(demands, resources)
        baseline_comp = NearestAvailableResourceBaseline.compare(opt_summary, base_summary)

        # 6. Calculate Simulation Delta if simulation run was evaluated
        if sim_run_record:
            # Run base state solver without scenario impact for delta comparison
            base_resources = EmergencyResourceExtractor.extract_from_db(self.db, resource_types=res_types, timestamp=ts_base) if self.db else copy.deepcopy(resources)
            base_opt_allocs, base_opt_summary = ORToolsEmergencySolver.solve(demands, base_resources, constraints)
            allocation_delta = OptimizationExplanationBuilder.build_allocation_delta(
                base_allocations=base_opt_allocs,
                sim_allocations=opt_allocations,
                base_summary=base_opt_summary,
                sim_summary=opt_summary
            )

        # 7. Construct Result Provenance
        run_uuid = str(uuid.uuid4())
        provenance_dict = {
            "run_id": run_uuid,
            "simulation_id": simulation_id,
            "engine_version": self.ENGINE_VERSION,
            "is_synthetic": True,
            "data_provenance_status": "model_optimization",
            "decision_support_warning": DECISION_SUPPORT_WARNING,
            "generated_at": now_utc.isoformat(),
            "assumptions": [
                "Travel costs are calculated via Haversine distance with accessibility penalties.",
                "Facility capacities are respected where known; unknown capacities use scenario defaults.",
                "Tie-breaking between equidistant facilities is strictly deterministic."
            ]
        }

        result = OptimizationResult(
            run_id=run_uuid,
            timestamp=now_utc.isoformat(),
            simulation_id=simulation_id,
            optimization_method=opt_method_name,
            objective_function="minimize_weighted_travel_cost",
            constraints=constraints.model_dump(),
            summary=opt_summary,
            allocations=opt_allocations,
            baseline_comparison=baseline_comp,
            allocation_delta=allocation_delta,
            provenance=provenance_dict,
            engine_version=self.ENGINE_VERSION
        )

        # 8. Persist to DB if requested
        if save and self.db:
            self._persist_optimization_run(result, ts_base, res_types, demands, resources)

        return result

    def _persist_optimization_run(
        self,
        result: OptimizationResult,
        ts_base: datetime,
        res_types: List[str],
        demands: List[EmergencyDemand],
        resources: List[EmergencyResource]
    ):
        demand_summary = {
            "total_demand_count": len(demands),
            "total_demand_quantity": result.summary.total_demand,
            "emergency_types": list(set(d.emergency_type for d in demands))
        }
        resource_summary = {
            "total_resource_count": len(resources),
            "resource_types": res_types,
            "utilization": result.summary.resource_utilization
        }

        opt_run = models.OptimizationRun(
            run_id=result.run_id,
            scenario_id=result.simulation_id,
            simulation_id=result.simulation_id,
            base_state_timestamp=ts_base,
            optimization_method=result.optimization_method,
            objective_function=result.objective_function,
            engine_version=self.ENGINE_VERSION,
            is_synthetic=True,
            constraints=result.constraints,
            resource_types=res_types,
            total_demand=result.summary.total_demand,
            served_demand=result.summary.served_demand,
            unserved_demand=result.summary.unserved_demand,
            total_travel_cost=result.summary.total_travel_cost,
            average_travel_cost=result.summary.average_travel_cost,
            demand_summary=demand_summary,
            resource_summary=resource_summary,
            allocation_results=[a.model_dump() for a in result.allocations],
            baseline_results=result.baseline_comparison.model_dump(),
            impact_comparison=result.allocation_delta,
            provenance=result.provenance
        )
        self.db.add(opt_run)
        self.db.commit()
        self.db.refresh(opt_run)
