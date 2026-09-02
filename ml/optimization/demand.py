from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from backend.app import models
from ml.optimization.schemas import EmergencyDemand
from ml.city_state.schema import CityState


class EmergencyDemandGenerator:
    """
    Generates standardized emergency demand inputs from ward populations,
    grid cells, or scenario parameters.
    """

    @staticmethod
    def generate_from_wards(
        db: Session,
        demand_rate_per_10k: float = 2.0,
        timestamp: Optional[datetime] = None
    ) -> List[EmergencyDemand]:
        """
        Generates ward-level emergency medical demand based on estimated ward population.
        """
        now_str = (timestamp or datetime.now(timezone.utc)).isoformat()
        demands: List[EmergencyDemand] = []

        wards = db.query(models.Ward).all()
        for w in wards:
            pop = w.population_est or 5000
            demand_qty = max(1, int(round((pop / 10000.0) * demand_rate_per_10k)))
            
            geom_obj = to_shape(w.geom) if w.geom is not None else None
            centroid = [float(geom_obj.centroid.x), float(geom_obj.centroid.y)] if geom_obj else [85.8246, 20.2961]

            # Assign priority based on demand size
            priority = "CRITICAL" if demand_qty >= 10 else ("HIGH" if demand_qty >= 5 else "NORMAL")
            p_weight = 3.0 if priority == "CRITICAL" else (1.5 if priority == "HIGH" else 1.0)

            demands.append(EmergencyDemand(
                demand_id=f"DEMAND_WARD_{w.ward_number}",
                spatial_id=f"WARD_{w.ward_number}",
                coordinates=centroid,
                timestamp=now_str,
                demand_quantity=demand_qty,
                emergency_type="medical",
                priority=priority,
                priority_weight=p_weight,
                source="ward_population_estimate",
                is_synthetic=True,
                provenance={
                    "ward_name": w.name,
                    "population": pop,
                    "demand_rate_per_10k": demand_rate_per_10k
                }
            ))

        return demands

    @staticmethod
    def generate_from_city_states(
        city_states: List[CityState],
        emergency_type: str = "medical"
    ) -> List[EmergencyDemand]:
        """
        Generates emergency demand points from CityState snapshots, reflecting simulated demand surges.
        """
        demands: List[EmergencyDemand] = []

        for idx, state in enumerate(city_states):
            loc = state.location
            coords = loc.centroid if loc and loc.centroid else [85.8246, 20.2961]
            pop = state.population.population_count if state.population else 500
            
            # Check if emergency service density or hazard level is elevated
            density = state.infrastructure.emergency_service_density if state.infrastructure else 1.0
            hazard_level = state.hazards.flood_risk_level if state.hazards else "LOW"

            base_qty = max(1, int(round((pop / 500.0) * density)))
            if hazard_level == "HIGH":
                base_qty *= 2
            elif hazard_level == "EXTREME":
                base_qty *= 3

            priority = "CRITICAL" if base_qty >= 8 or hazard_level == "HIGH" else ("HIGH" if base_qty >= 4 else "NORMAL")
            p_weight = 3.0 if priority == "CRITICAL" else (1.5 if priority == "HIGH" else 1.0)

            demands.append(EmergencyDemand(
                demand_id=f"DEMAND_CS_{loc.spatial_id or idx}",
                spatial_id=loc.spatial_id or f"CS_{idx}",
                coordinates=coords,
                timestamp=state.time.state_timestamp if state.time else datetime.now(timezone.utc).isoformat(),
                demand_quantity=base_qty,
                emergency_type=emergency_type,
                priority=priority,
                priority_weight=p_weight,
                source="simulated_city_state",
                is_synthetic=True,
                provenance={
                    "hazard_level": hazard_level,
                    "emergency_density": density,
                    "population": pop
                }
            ))

        return demands
