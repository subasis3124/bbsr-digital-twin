from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from backend.app import models
from ml.optimization.schemas import EmergencyResource
from ml.city_state.schema import CityState


class EmergencyResourceExtractor:
    """
    Extracts and standardizes emergency infrastructure resources from DB models
    or CityState payloads.
    """

    @staticmethod
    def extract_from_db(
        db: Session,
        resource_types: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None
    ) -> List[EmergencyResource]:
        """
        Loads emergency resources directly from PostGIS tables.
        """
        if not resource_types:
            resource_types = ["hospital", "police_station", "fire_station"]

        now_str = (timestamp or datetime.now(timezone.utc)).isoformat()
        resources: List[EmergencyResource] = []

        if "hospital" in resource_types:
            hospitals = db.query(models.Hospital).all()
            for h in hospitals:
                geom_obj = to_shape(h.geom) if h.geom is not None else None
                coords = [float(geom_obj.x), float(geom_obj.y)] if geom_obj else [85.8246, 20.2961]
                
                # Check bed capacity: if beds <= 0, mark as unknown
                beds_val = getattr(h, "beds", 0)
                if beds_val is None or beds_val <= 0:
                    cap = None
                    cap_status = "unknown"
                    avail_cap = 50  # default scenario capacity when capacity is unknown, marked as scenario-defined
                else:
                    cap = beds_val
                    cap_status = "known"
                    avail_cap = cap

                resources.append(EmergencyResource(
                    resource_id=f"HOSP_{h.id}",
                    resource_type="hospital",
                    name=h.name or f"Hospital_{h.id}",
                    coordinates=coords,
                    capacity=cap,
                    capacity_status=cap_status,
                    available_capacity=avail_cap,
                    accessibility=1.0,
                    status="AVAILABLE",
                    timestamp=now_str,
                    metadata={"osm_id": float(h.osm_id) if h.osm_id else None, "raw_beds": beds_val},
                    provenance={
                        "source_table": "hospitals",
                        "is_synthetic": False,
                        "data_provenance_status": "observed"
                    }
                ))

        if "police_station" in resource_types:
            police = db.query(models.PoliceStation).all()
            for p in police:
                geom_obj = to_shape(p.geom) if p.geom is not None else None
                coords = [float(geom_obj.x), float(geom_obj.y)] if geom_obj else [85.8246, 20.2961]

                resources.append(EmergencyResource(
                    resource_id=f"POLICE_{p.id}",
                    resource_type="police_station",
                    name=p.name or f"Police_Station_{p.id}",
                    coordinates=coords,
                    capacity=None,
                    capacity_status="unknown",
                    available_capacity=20,  # scenario-supplied default capacity for dispatch
                    accessibility=1.0,
                    status="AVAILABLE",
                    timestamp=now_str,
                    metadata={"osm_id": float(p.osm_id) if p.osm_id else None},
                    provenance={
                        "source_table": "police_stations",
                        "is_synthetic": False,
                        "data_provenance_status": "observed"
                    }
                ))

        if "fire_station" in resource_types:
            fire = db.query(models.FireStation).all()
            for f in fire:
                geom_obj = to_shape(f.geom) if f.geom is not None else None
                coords = [float(geom_obj.x), float(geom_obj.y)] if geom_obj else [85.8246, 20.2961]

                resources.append(EmergencyResource(
                    resource_id=f"FIRE_{f.id}",
                    resource_type="fire_station",
                    name=f.name or f"Fire_Station_{f.id}",
                    coordinates=coords,
                    capacity=None,
                    capacity_status="unknown",
                    available_capacity=15,  # scenario-supplied default capacity for dispatch
                    accessibility=1.0,
                    status="AVAILABLE",
                    timestamp=now_str,
                    metadata={"osm_id": float(f.osm_id) if f.osm_id else None},
                    provenance={
                        "source_table": "fire_stations",
                        "is_synthetic": False,
                        "data_provenance_status": "observed"
                    }
                ))

        return resources

    @staticmethod
    def extract_from_city_states(
        city_states: List[CityState],
        resource_types: Optional[List[str]] = None
    ) -> List[EmergencyResource]:
        """
        Extracts or updates emergency resource accessibility and capacities from
        canonical CityState snapshots (e.g., modified by what-if simulations).
        """
        resources: List[EmergencyResource] = []
        # If city states include explicit infrastructure/accessibility info, map it:
        for idx, state in enumerate(city_states):
            acc = state.mobility.road_accessibility if state.mobility else 1.0
            loc = state.location
            coords = loc.centroid if loc and loc.centroid else [85.8246, 20.2961]
            
            # Map hospital count if present
            h_count = state.infrastructure.hospitals_count if state.infrastructure else 0
            if h_count > 0:
                status = "AVAILABLE" if acc > 0.5 else ("DEGRADED" if acc > 0.05 else "INACCESSIBLE")
                resources.append(EmergencyResource(
                    resource_id=f"HOSP_CS_{loc.spatial_id or idx}",
                    resource_type="hospital",
                    name=f"Hospital Sector {loc.spatial_id or idx}",
                    coordinates=coords,
                    capacity=50 * h_count,
                    capacity_status="scenario_defined",
                    available_capacity=50 * h_count,
                    accessibility=acc,
                    status=status,
                    timestamp=state.time.state_timestamp if state.time else datetime.now(timezone.utc).isoformat(),
                    provenance={
                        "source": "city_state",
                        "is_synthetic": state.provenance.is_synthetic if state.provenance else True
                    }
                ))
        return resources
