import math
from typing import List, Dict, Tuple, Any, Optional

from ml.optimization.schemas import EmergencyDemand, EmergencyResource

INACCESSIBLE_COST = 999999.0


class TravelCostCalculator:
    """
    Computes spatial travel matrix and accessibility-weighted costs
    between emergency demands and resources.
    """

    @staticmethod
    def haversine_distance_km(coord1: List[float], coord2: List[float]) -> float:
        """
        Calculates Great-Circle Haversine distance in kilometers between two [lon, lat] points.
        """
        lon1, lat1 = coord1[0], coord1[1]
        lon2, lat2 = coord2[0], coord2[1]

        R = 6371.0  # Earth radius in kilometers

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

        return round(R * c, 4)

    @classmethod
    def compute_travel_cost(
        cls,
        demand: EmergencyDemand,
        resource: EmergencyResource,
        speed_kmh: float = 40.0
    ) -> Tuple[float, float, str]:
        """
        Computes travel cost between a demand point and emergency resource facility.
        Returns: (effective_cost, raw_distance_km, cost_unit)
        """
        dist_km = cls.haversine_distance_km(demand.coordinates, resource.coordinates)

        # Check resource accessibility status
        acc = resource.accessibility
        if acc <= 0.05 or resource.status == "INACCESSIBLE":
            return INACCESSIBLE_COST, dist_km, "inaccessible"

        # Apply accessibility factor penalty: as accessibility drops below 1.0, travel cost increases
        accessibility_penalty = 1.0 / max(0.01, acc)
        effective_cost = round(dist_km * accessibility_penalty, 3)

        return effective_cost, dist_km, "km"

    @classmethod
    def compute_cost_matrix(
        cls,
        demands: List[EmergencyDemand],
        resources: List[EmergencyResource]
    ) -> Dict[Tuple[str, str], float]:
        """
        Builds a lookup map: (demand_id, resource_id) -> travel_cost.
        """
        matrix: Dict[Tuple[str, str], float] = {}

        for d in demands:
            for r in resources:
                cost, _, _ = cls.compute_travel_cost(d, r)
                matrix[(d.demand_id, r.resource_id)] = cost

        return matrix
