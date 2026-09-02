from typing import List, Dict, Any
from ml.simulation.schemas import TransformationStep

class DependencyGraph:
    """
    Explicit Dependency Propagation Graph for What-If Simulations.
    Tracks transformation chains across environmental, hazard, mobility, infrastructure,
    and derived layers to ensure full transparency and auditability.
    """

    def __init__(self):
        self.steps: List[TransformationStep] = []
        self.edges: List[Dict[str, str]] = []

    def add_step(
        self,
        step_number: int,
        name: str,
        layer_affected: str,
        input_variables: Dict[str, Any],
        output_variables: Dict[str, Any],
        method: str,
        description: str,
        depends_on: List[str] = None
    ):
        step = TransformationStep(
            step_number=step_number,
            name=name,
            layer_affected=layer_affected,
            input_variables=input_variables,
            output_variables=output_variables,
            method=method,
            description=description
        )
        self.steps.append(step)

        if depends_on:
            for dep in depends_on:
                self.edges.append({"from": dep, "to": name})

    def get_steps(self) -> List[TransformationStep]:
        return self.steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.model_dump() for s in self.steps],
            "dependency_edges": self.edges
        }
