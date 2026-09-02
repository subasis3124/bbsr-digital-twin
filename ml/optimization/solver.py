from typing import List, Dict, Tuple, Any, Optional
import math
from ortools.linear_solver import pywraplp

from ml.optimization.schemas import (
    EmergencyDemand, EmergencyResource, DemandAssignment,
    OptimizationConstraints, OptimizationSummary
)
from ml.optimization.travel_cost import TravelCostCalculator, INACCESSIBLE_COST


class ORToolsEmergencySolver:
    """
    Decision-Support Optimization Engine powered by Google OR-Tools.
    Formulates and solves Capacitated Facility Assignment & Emergency Dispatch as a Min-Cost Flow / MILP.
    """

    UNSERVED_PENALTY = 10000.0

    @classmethod
    def solve(
        cls,
        demands: List[EmergencyDemand],
        resources: List[EmergencyResource],
        constraints: Optional[OptimizationConstraints] = None
    ) -> Tuple[List[DemandAssignment], OptimizationSummary]:
        """
        Solves optimal assignment of emergency demand points to emergency resources using OR-Tools CBC/GLOP solver.
        """
        if not constraints:
            constraints = OptimizationConstraints()

        # Sort demands and resources deterministically by ID to ensure strict reproducibility
        sorted_demands = sorted(demands, key=lambda d: d.demand_id)
        sorted_resources = sorted(resources, key=lambda r: r.resource_id)

        # Create OR-Tools solver (CBC linear solver)
        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            # Fallback solver if CBC unavailable in environment
            solver = pywraplp.Solver.CreateSolver("GLOP")

        # Define Decision Variables
        # x[i, j]: integer/continuous allocation of demand i to resource j
        x: Dict[Tuple[int, int], Any] = {}
        # u[i]: unserved demand for demand point i
        u: Dict[int, Any] = {}

        N = len(sorted_demands)
        M = len(sorted_resources)

        for i, d in enumerate(sorted_demands):
            u[i] = solver.IntVar(0, d.demand_quantity, f"u_{i}")
            for j, r in enumerate(sorted_resources):
                # Max allocation bounded by demand quantity
                x[i, j] = solver.IntVar(0, d.demand_quantity, f"x_{i}_{j}")

        # Compute cost matrix and build Objective Function
        objective = solver.Objective()

        # Epsilon factor for deterministic tie-breaking (order by resource_id)
        eps = 1e-6

        for i, d in enumerate(sorted_demands):
            # Penalty for leaving demand unserved
            objective.SetCoefficient(u[i], cls.UNSERVED_PENALTY)

            p_weight = d.priority_weight if constraints.priority_weighting else 1.0

            for j, r in enumerate(sorted_resources):
                cost, _, _ = TravelCostCalculator.compute_travel_cost(d, r)
                
                # Check max travel cost constraint
                if constraints.max_travel_cost and cost > constraints.max_travel_cost and cost < INACCESSIBLE_COST:
                    cost = INACCESSIBLE_COST

                if cost >= INACCESSIBLE_COST or r.status == "INACCESSIBLE" or r.accessibility <= 0.05:
                    # Inaccessible facility constraint: fix allocation to 0
                    solver.Add(x[i, j] == 0)
                else:
                    # Objective coefficient: weighted travel cost with deterministic tie-breaker
                    coeff = (cost * p_weight) + (j * eps)
                    objective.SetCoefficient(x[i, j], float(coeff))

        objective.SetMinimization()

        # Constraint 1: Demand Satisfaction (sum_j x[i,j] + u[i] == demand_i)
        for i, d in enumerate(sorted_demands):
            demand_constraint = solver.Constraint(d.demand_quantity, d.demand_quantity, f"demand_sat_{i}")
            demand_constraint.SetCoefficient(u[i], 1)
            for j in range(M):
                demand_constraint.SetCoefficient(x[i, j], 1)

        # Constraint 2: Facility Capacity Constraint (sum_i x[i,j] <= capacity_j)
        for j, r in enumerate(sorted_resources):
            if constraints.capacity_constrained and r.capacity is not None and r.capacity > 0:
                cap_val = r.available_capacity if r.available_capacity > 0 else r.capacity
                cap_constraint = solver.Constraint(0, cap_val, f"facility_cap_{j}")
                for i in range(N):
                    cap_constraint.SetCoefficient(x[i, j], 1)

        # Solve Problem
        solver.set_time_limit(10000)  # 10 second timeout
        status = solver.Solve()

        allocations: List[DemandAssignment] = []
        resource_used: Dict[str, int] = {r.resource_id: 0 for r in sorted_resources}
        
        total_demand_qty = sum(d.demand_quantity for d in sorted_demands)
        served_demand_qty = 0
        unserved_demand_qty = 0
        total_travel_cost = 0.0
        max_travel_cost = 0.0

        bottlenecks: List[str] = []
        inaccessible_resources: List[str] = [r.resource_id for r in sorted_resources if r.accessibility <= 0.05 or r.status == "INACCESSIBLE"]
        constraint_violations: List[str] = []

        if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            constraint_violations.append("Solver failed to find an optimal solution. Falling back to default assignment.")

        # Process Results
        for i, d in enumerate(sorted_demands):
            unserved_qty = int(round(u[i].solution_value())) if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE) else d.demand_quantity
            assigned_total_for_d = 0

            for j, r in enumerate(sorted_resources):
                alloc_qty = int(round(x[i, j].solution_value())) if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE) else 0
                if alloc_qty > 0:
                    cost, raw_dist, _ = TravelCostCalculator.compute_travel_cost(d, r)
                    assigned_total_for_d += alloc_qty
                    resource_used[r.resource_id] += alloc_qty
                    
                    travel_cost_contrib = cost * alloc_qty
                    total_travel_cost += travel_cost_contrib
                    if cost > max_travel_cost and cost < INACCESSIBLE_COST:
                        max_travel_cost = cost

                    expl = (
                        f"Demand {d.demand_id} ({d.demand_quantity} unit(s), priority {d.priority}) "
                        f"assigned {alloc_qty} case(s) to facility {r.name} ({r.resource_id}) "
                        f"at travel cost {cost:.2f}km under optimal min-cost formulation."
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

            unserved_remainder = d.demand_quantity - assigned_total_for_d
            if unserved_remainder > 0:
                unserved_demand_qty += unserved_remainder
                expl = (
                    f"Demand {d.demand_id} had {unserved_remainder} case(s) UNSERVED due to "
                    f"facility capacity saturation or network accessibility constraints."
                )
                allocations.append(DemandAssignment(
                    demand_id=d.demand_id,
                    assigned_resource_id=None,
                    resource_type=d.emergency_type,
                    allocation_quantity=unserved_remainder,
                    travel_cost=INACCESSIBLE_COST,
                    travel_cost_unit="km",
                    accessibility=0.0,
                    priority=d.priority,
                    assignment_status="UNSERVED",
                    explanation=expl
                ))

            served_demand_qty += assigned_total_for_d

        # Calculate resource utilization and detect bottlenecks
        resource_util: Dict[str, Dict[str, Any]] = {}
        for r in sorted_resources:
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
            constraint_violations=constraint_violations
        )

        return allocations, summary
