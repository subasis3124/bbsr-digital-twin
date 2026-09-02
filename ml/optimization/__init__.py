"""
Phase 13 — Emergency Resource Optimization Module.
Provides decision-support optimization engines to allocate emergency resources
(hospitals, police stations, fire stations) under base and simulated urban states.
"""

from ml.optimization.schemas import (
    EmergencyDemand, EmergencyResource, DemandAssignment,
    OptimizationConstraints, OptimizationRequest, OptimizationResult,
    OptimizationSummary, BaselineComparison
)
from ml.optimization.engine import EmergencyOptimizationEngine

__all__ = [
    "EmergencyDemand",
    "EmergencyResource",
    "DemandAssignment",
    "OptimizationConstraints",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizationSummary",
    "BaselineComparison",
    "EmergencyOptimizationEngine"
]
