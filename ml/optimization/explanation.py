from typing import List, Dict, Any, Optional
from ml.optimization.schemas import DemandAssignment, OptimizationSummary, BaselineComparison


class OptimizationExplanationBuilder:
    """
    Generates explainability metadata, decision provenance, and impact summaries
    for emergency resource allocations.
    """

    @staticmethod
    def build_allocation_delta(
        base_allocations: List[DemandAssignment],
        sim_allocations: List[DemandAssignment],
        base_summary: OptimizationSummary,
        sim_summary: OptimizationSummary
    ) -> Dict[str, Any]:
        """
        Calculates allocation changes (deltas) when comparing a Base State optimization
        against a What-If Simulated State optimization (e.g. road closure or flood event).
        """
        base_map = {a.demand_id: a for a in base_allocations if a.assigned_resource_id}
        sim_map = {a.demand_id: a for a in sim_allocations if a.assigned_resource_id}

        reassigned_demands: List[Dict[str, Any]] = []

        all_demand_ids = set(base_map.keys()).union(set(sim_map.keys()))

        for d_id in sorted(all_demand_ids):
            b_alloc = base_map.get(d_id)
            s_alloc = sim_map.get(d_id)

            if b_alloc and s_alloc:
                if b_alloc.assigned_resource_id != s_alloc.assigned_resource_id:
                    reassigned_demands.append({
                        "demand_id": d_id,
                        "base_assigned_resource": b_alloc.assigned_resource_id,
                        "simulated_assigned_resource": s_alloc.assigned_resource_id,
                        "base_travel_cost": b_alloc.travel_cost,
                        "simulated_travel_cost": s_alloc.travel_cost,
                        "cost_delta": round(s_alloc.travel_cost - b_alloc.travel_cost, 2),
                        "reason": f"Reassigned from {b_alloc.assigned_resource_id} to {s_alloc.assigned_resource_id} due to simulated road accessibility or capacity shifts."
                    })
            elif b_alloc and not s_alloc:
                reassigned_demands.append({
                    "demand_id": d_id,
                    "base_assigned_resource": b_alloc.assigned_resource_id,
                    "simulated_assigned_resource": None,
                    "base_travel_cost": b_alloc.travel_cost,
                    "simulated_travel_cost": 999999.0,
                    "cost_delta": 999999.0,
                    "reason": f"Demand became UNSERVED under scenario due to facility inaccessibility or network disruption."
                })
            elif not b_alloc and s_alloc:
                reassigned_demands.append({
                    "demand_id": d_id,
                    "base_assigned_resource": None,
                    "simulated_assigned_resource": s_alloc.assigned_resource_id,
                    "base_travel_cost": 999999.0,
                    "simulated_travel_cost": s_alloc.travel_cost,
                    "cost_delta": -s_alloc.travel_cost,
                    "reason": f"Newly served demand allocated to {s_alloc.assigned_resource_id} under scenario."
                })

        total_cost_delta = round(sim_summary.total_travel_cost - base_summary.total_travel_cost, 2)
        unserved_delta = sim_summary.unserved_demand - base_summary.unserved_demand

        return {
            "total_travel_cost_delta": total_cost_delta,
            "avg_travel_cost_delta": round(sim_summary.average_travel_cost - base_summary.average_travel_cost, 3),
            "unserved_demand_delta": unserved_delta,
            "reassigned_demands_count": len(reassigned_demands),
            "reassigned_demands": reassigned_demands,
            "summary_text": (
                f"What-If scenario resulted in {len(reassigned_demands)} demand reassignments, "
                f"a travel cost change of {total_cost_delta:+.2f}km, and an unserved demand change of {unserved_delta:+d}."
            )
        }
