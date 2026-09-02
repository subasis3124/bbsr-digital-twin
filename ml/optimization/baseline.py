from typing import List, Dict, Tuple, Any, Optional
import copy

from ml.optimization.schemas import (
    EmergencyDemand, EmergencyResource, DemandAssignment,
    OptimizationSummary, BaselineComparison
)
from ml.optimization.travel_cost import TravelCostCalculator, INACCESSIBLE_COST


class NearestAvailableResourceBaseline:
    """
    Baseline Heuristic Dispatcher.
    Greedily assigns emergency demand points to the nearest available and accessible facility.
    Used as benchmark to measure optimization gain.
    """

    @classmethod
    def solve(
        cls,
        demands: List[EmergencyDemand],
        resources: List[EmergencyResource]
    ) -> Tuple[List[DemandAssignment], OptimizationSummary]:
        """
        Executes Nearest Available Resource baseline assignment algorithm.
        """
        # Priority ranking dictionary for sorting
        prio_rank = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2}

        # Sort demands deterministically by priority rank then demand_id
        sorted_demands = sorted(demands, key=lambda d: (prio_rank.get(d.priority, 3), d.demand_id))
        
        # Track remaining available capacity per resource
        resource_caps: Dict[str, int] = {
            r.resource_id: (r.available_capacity if r.available_capacity > 0 else (r.capacity or 9999))
            for r in resources
        }
        resource_map: Dict[str, EmergencyResource] = {r.resource_id: r for r in resources}

        allocations: List[DemandAssignment] = []
        resource_used: Dict[str, int] = {r.resource_id: 0 for r in resources}

        total_demand_qty = sum(d.demand_quantity for d in sorted_demands)
        served_demand_qty = 0
        unserved_demand_qty = 0
        total_travel_cost = 0.0
        max_travel_cost = 0.0

        bottlenecks: List[str] = []
        inaccessible_resources: List[str] = [r.resource_id for r in resources if r.accessibility <= 0.05 or r.status == "INACCESSIBLE"]

        for d in sorted_demands:
            remaining_demand = d.demand_quantity

            # Sort accessible resources by travel cost to demand point
            candidate_resources = []
            for r in resources:
                if r.accessibility > 0.05 and r.status != "INACCESSIBLE":
                    cost, raw_dist, _ = TravelCostCalculator.compute_travel_cost(d, r)
                    if cost < INACCESSIBLE_COST:
                        candidate_resources.append((cost, r))

            candidate_resources.sort(key=lambda item: (item[0], item[1].resource_id))

            for cost, r in candidate_resources:
                if remaining_demand <= 0:
                    break

                avail = resource_caps[r.resource_id]
                if avail > 0:
                    alloc_qty = min(remaining_demand, avail)
                    resource_caps[r.resource_id] -= alloc_qty
                    resource_used[r.resource_id] += alloc_qty
                    remaining_demand -= alloc_qty
                    
                    total_travel_cost += cost * alloc_qty
                    if cost > max_travel_cost:
                        max_travel_cost = cost

                    expl = (
                        f"[BASELINE: Nearest Available] Demand {d.demand_id} assigned {alloc_qty} case(s) "
                        f"to nearest accessible facility {r.name} ({r.resource_id}) at distance/cost {cost:.2f}km."
                    )

                    allocations.append(DemandAssignment(
                        demand_id=d.demand_id,
                        assigned_resource_id=r.resource_id,
                        resource_type=r.resource_type,
                        allocation_quantity=alloc_qty,
                        travel_cost=cost,
                        travel_cost_unit="km",
                        accessibility=r.accessibility,
                        priority=d.priority,
                        assignment_status="ASSIGNED",
                        explanation=expl
                    ))

            if remaining_demand > 0:
                unserved_demand_qty += remaining_demand
                expl = (
                    f"[BASELINE: Nearest Available] Demand {d.demand_id} had {remaining_demand} case(s) UNSERVED "
                    f"because all nearby candidate facilities reached capacity."
                )
                allocations.append(DemandAssignment(
                    demand_id=d.demand_id,
                    assigned_resource_id=None,
                    resource_type=d.emergency_type,
                    allocation_quantity=remaining_demand,
                    travel_cost=INACCESSIBLE_COST,
                    travel_cost_unit="km",
                    accessibility=0.0,
                    priority=d.priority,
                    assignment_status="UNSERVED",
                    explanation=expl
                ))
            else:
                served_demand_qty += d.demand_quantity

        # Utilization calculation
        resource_util: Dict[str, Dict[str, Any]] = {}
        for r in resources:
            used = resource_used.get(r.resource_id, 0)
            cap = r.available_capacity if r.available_capacity > 0 else (r.capacity or 100)
            util_ratio = round(used / float(cap), 4) if cap > 0 else 0.0
            
            if util_ratio >= 0.95 and used > 0:
                bottlenecks.append(r.resource_id)

            resource_util[r.resource_id] = {
                "name": r.name,
                "used_capacity": used,
                "total_capacity": cap,
                "utilization_ratio": util_ratio,
                "accessibility": r.accessibility,
                "status": r.status
            }

        avg_travel_cost = round(total_travel_cost / float(max(1, served_demand_qty)), 3)

        summary = OptimizationSummary(
            total_demand=total_demand_qty,
            served_demand=served_demand_qty,
            unserved_demand=unserved_demand_qty,
            total_travel_cost=round(total_travel_cost, 2),
            average_travel_cost=avg_travel_cost,
            max_travel_cost=round(max_travel_cost, 2),
            resource_utilization=resource_util,
            bottlenecks=bottlenecks,
            inaccessible_resources=inaccessible_resources,
            constraint_violations=[]
        )

        return allocations, summary

    @classmethod
    def compare(
        cls,
        opt_summary: OptimizationSummary,
        base_summary: OptimizationSummary
    ) -> BaselineComparison:
        """
        Compares OR-Tools optimal summary against Nearest Available baseline summary.
        """
        cost_diff = round(opt_summary.total_travel_cost - base_summary.total_travel_cost, 2)
        avg_cost_diff = round(opt_summary.average_travel_cost - base_summary.average_travel_cost, 3)
        unserved_diff = opt_summary.unserved_demand - base_summary.unserved_demand

        if base_summary.total_travel_cost > 0:
            improvement_pct = round(((base_summary.total_travel_cost - opt_summary.total_travel_cost) / base_summary.total_travel_cost) * 100.0, 2)
        else:
            improvement_pct = 0.0

        if improvement_pct > 0:
            sum_str = f"Optimized allocation reduced travel cost by {improvement_pct}% compared to nearest-resource baseline."
        elif improvement_pct == 0:
            sum_str = "Optimized allocation matched baseline performance."
        else:
            sum_str = f"Optimized allocation prioritized global demand satisfaction and capacity constraints over unconstrained nearest assignment."

        return BaselineComparison(
            baseline_method="NEAREST_AVAILABLE_RESOURCE",
            total_travel_cost_diff=cost_diff,
            avg_travel_cost_diff=avg_cost_diff,
            unserved_demand_diff=unserved_diff,
            improvement_percentage=improvement_pct,
            comparison_summary=sum_str
        )
