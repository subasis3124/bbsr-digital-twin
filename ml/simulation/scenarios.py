from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import copy
from datetime import datetime, timezone

from ml.city_state.schema import CityState
from ml.simulation.schemas import (
    SimulationScenario, TransformationStep, HeavyRainfallParams,
    RoadClosureParams, AirPollutionParams, EmergencyDemandParams, SpatialScope
)
from ml.simulation.dependency import DependencyGraph

HEURISTIC_WARNING = "WARNING: This result is a scenario perturbation and is not a calibrated physical simulation."

class BaseScenario(ABC):
    """
    Abstract Base Class for modular What-If Simulation Scenarios.
    """
    scenario_type: str = "base"
    scenario_name: str = "Base Scenario"

    @abstractmethod
    def apply(self, base_state: CityState) -> Tuple[CityState, List[TransformationStep]]:
        """
        Applies scenario transformations to a base CityState instance.
        Returns a new simulated CityState (immutable original) and the inspectable transformation steps.
        """
        pass

    @staticmethod
    def is_in_scope(state: CityState, scope: SpatialScope) -> bool:
        """
        Evaluates whether a given CityState falls within the spatial scope filter.
        """
        if not scope or scope.scope_type == "all":
            return True

        loc = state.location
        if scope.scope_type == "grid_cell" or scope.cell_codes:
            if loc.cell_code and loc.cell_code in scope.cell_codes:
                return True
            if loc.spatial_id in scope.cell_codes:
                return True

        if scope.scope_type == "ward" or scope.ward_ids:
            if loc.ward_number and loc.ward_number in scope.ward_ids:
                return True
            if loc.ward_id and loc.ward_id in scope.ward_ids:
                return True

        if scope.scope_type == "road" or scope.road_ids:
            if loc.road_id and loc.road_id in scope.road_ids:
                return True

        if scope.scope_type == "bbox" or (scope.min_lon is not None and scope.max_lon is not None):
            if loc.centroid and len(loc.centroid) >= 2:
                lon, lat = loc.centroid[0], loc.centroid[1]
                if (scope.min_lon <= lon <= scope.max_lon) and (scope.min_lat <= lat <= scope.max_lat):
                    return True
            return False

        return False


class HeavyRainfallScenario(BaseScenario):
    """
    Heavy Rainfall Perturbation Scenario.
    Propagates: Rainfall -> Flood Risk -> Road Accessibility -> Traffic Congestion & Speed -> Derived Indicators
    """
    scenario_type = "heavy_rainfall"
    scenario_name = "Heavy Rainfall Simulation Scenario"

    def __init__(self, params: HeavyRainfallParams):
        self.params = params

    def apply(self, base_state: CityState) -> Tuple[CityState, List[TransformationStep]]:
        # Clone base state to maintain immutability
        state_dict = copy.deepcopy(base_state.model_dump())
        sim_state = CityState(**state_dict)

        graph = DependencyGraph()

        if not self.is_in_scope(sim_state, self.params.spatial_scope):
            return sim_state, []

        base_rainfall = sim_state.environment.rainfall or 0.0
        base_flood_prob = sim_state.hazards.flood_risk_probability or 0.05
        base_speed = sim_state.mobility.observed_speed or 40.0
        base_cong = sim_state.mobility.congestion_ratio or 0.2

        # Step 1: Environmental Rainfall Transformation
        rainfall_sim = round(base_rainfall * self.params.rainfall_multiplier + self.params.rainfall_delta_mm, 2)
        sim_state.environment.rainfall = rainfall_sim

        if rainfall_sim > 50.0:
            rainfall_cat = "EXTREME"
        elif rainfall_sim > 20.0:
            rainfall_cat = "HEAVY"
        elif rainfall_sim > 5.0:
            rainfall_cat = "MODERATE"
        elif rainfall_sim > 0.0:
            rainfall_cat = "LIGHT"
        else:
            rainfall_cat = "NONE"

        graph.add_step(
            step_number=1,
            name="Environmental Rainfall Perturbation",
            layer_affected="environment",
            input_variables={"rainfall_multiplier": self.params.rainfall_multiplier, "rainfall_delta_mm": self.params.rainfall_delta_mm, "base_rainfall": base_rainfall},
            output_variables={"simulated_rainfall": rainfall_sim, "rainfall_category": rainfall_cat},
            method="heuristic_simulation",
            description="Calculated simulated rainfall value based on input multiplier and delta."
        )

        # Step 2: Flood Risk Recalculation
        if rainfall_sim > 50.0:
            flood_prob_sim = min(1.0, max(base_flood_prob + 0.45, 0.75))
        elif rainfall_sim > 20.0:
            flood_prob_sim = min(1.0, max(base_flood_prob + 0.30, 0.50))
        elif rainfall_sim > 5.0:
            flood_prob_sim = min(1.0, max(base_flood_prob + 0.15, 0.25))
        else:
            flood_prob_sim = base_flood_prob

        flood_prob_sim = round(flood_prob_sim, 4)
        flood_level_sim = "HIGH" if flood_prob_sim >= 0.70 else ("MODERATE" if flood_prob_sim >= 0.40 else "LOW")
        active_flood = flood_prob_sim > 0.5

        sim_state.hazards.flood_risk_probability = flood_prob_sim
        sim_state.hazards.flood_risk_level = flood_level_sim
        sim_state.hazards.active_flood_event = active_flood
        sim_state.hazards.severity = "HIGH" if flood_prob_sim > 0.7 else "NORMAL"

        graph.add_step(
            step_number=2,
            name="Flood Risk Recalculation",
            layer_affected="hazards",
            input_variables={"simulated_rainfall": rainfall_sim, "base_flood_probability": base_flood_prob},
            output_variables={"simulated_flood_probability": flood_prob_sim, "flood_risk_level": flood_level_sim, "active_flood_event": active_flood},
            method="heuristic_simulation",
            description="Propagated rainfall intensity to flood risk probability and hazard severity level.",
            depends_on=["Environmental Rainfall Perturbation"]
        )

        # Step 3: Road Accessibility Recalculation
        road_acc_sim = max(0.0, round(1.0 - flood_prob_sim, 2))
        sim_state.mobility.road_accessibility = road_acc_sim

        graph.add_step(
            step_number=3,
            name="Road Accessibility Recalculation",
            layer_affected="mobility",
            input_variables={"simulated_flood_probability": flood_prob_sim},
            output_variables={"road_accessibility": road_acc_sim},
            method="heuristic_simulation",
            description="Reduced road network accessibility proportionally to flood hazard level.",
            depends_on=["Flood Risk Recalculation"]
        )

        # Step 4: Traffic / Mobility Impact Propagation
        speed_sim = round(max(0.0, base_speed * road_acc_sim), 1)
        cong_sim = round(min(2.0, base_cong * (1.0 + flood_prob_sim * 1.5)), 2)

        sim_state.mobility.observed_speed = speed_sim
        sim_state.mobility.forecast_speed = speed_sim
        sim_state.mobility.congestion_ratio = cong_sim
        sim_state.mobility.forecast_congestion_ratio = cong_sim

        graph.add_step(
            step_number=4,
            name="Traffic Mobility Impact Propagation",
            layer_affected="mobility",
            input_variables={"base_speed": base_speed, "road_accessibility": road_acc_sim, "base_congestion": base_cong},
            output_variables={"simulated_speed": speed_sim, "simulated_congestion_ratio": cong_sim},
            method="heuristic_simulation",
            description="Propagated reduced road accessibility to lower traffic speeds and heightened congestion ratios.",
            depends_on=["Road Accessibility Recalculation"]
        )

        # Step 5: Derived Indicators Update
        sim_state.derived.traffic_congestion_index = cong_sim
        sim_state.derived.flood_risk_level = flood_level_sim
        sim_state.derived.rainfall_intensity = rainfall_cat
        sim_state.derived.road_accessibility = road_acc_sim

        graph.add_step(
            step_number=5,
            name="Derived Indicators Synthesis",
            layer_affected="derived",
            input_variables={"simulated_congestion": cong_sim, "flood_level": flood_level_sim, "rainfall_cat": rainfall_cat},
            output_variables={"derived_indicators": sim_state.derived.model_dump()},
            method="heuristic_simulation",
            description="Synthesized derived city state indicators for front-end query rendering.",
            depends_on=["Traffic Mobility Impact Propagation"]
        )

        # Provenance Update
        sim_state.provenance.is_synthetic = True
        sim_state.provenance.data_provenance_status = "scenario_simulation"
        sim_state.provenance.scientific_validation_warning = HEURISTIC_WARNING
        if "heavy_rainfall_scenario" not in sim_state.provenance.sources:
            sim_state.provenance.sources.append("heavy_rainfall_scenario")

        return sim_state, graph.get_steps()


class RoadClosureScenario(BaseScenario):
    """
    Road Closure Scenario.
    Propagates: Road Status (Closed) -> Zero Accessibility -> Detour Network Congestion & Speed Drop -> Derived Indicators
    """
    scenario_type = "road_closure"
    scenario_name = "Road Closure Simulation Scenario"

    def __init__(self, params: RoadClosureParams):
        self.params = params

    def apply(self, base_state: CityState) -> Tuple[CityState, List[TransformationStep]]:
        state_dict = copy.deepcopy(base_state.model_dump())
        sim_state = CityState(**state_dict)

        graph = DependencyGraph()

        loc = sim_state.location
        road_id = loc.road_id
        spatial_id = loc.spatial_id

        is_directly_closed = False
        if road_id and road_id in self.params.closed_road_ids:
            is_directly_closed = True
        elif spatial_id and spatial_id.isdigit() and int(spatial_id) in self.params.closed_road_ids:
            is_directly_closed = True

        if not is_directly_closed and not self.is_in_scope(sim_state, self.params.spatial_scope):
            return sim_state, []

        base_speed = sim_state.mobility.observed_speed or 40.0
        base_cong = sim_state.mobility.congestion_ratio or 0.2

        if is_directly_closed:
            # Step 1: Direct Road Closure Transformation
            sim_state.mobility.road_accessibility = 0.0
            sim_state.mobility.observed_speed = 0.0
            sim_state.mobility.forecast_speed = 0.0
            sim_state.mobility.congestion_ratio = 2.0
            sim_state.mobility.forecast_congestion_ratio = 2.0
            sim_state.mobility.status = "CLOSED"

            graph.add_step(
                step_number=1,
                name="Direct Road Segment Closure",
                layer_affected="mobility",
                input_variables={"closed_road_id": road_id or spatial_id},
                output_variables={"road_accessibility": 0.0, "observed_speed": 0.0, "status": "CLOSED"},
                method="heuristic_simulation",
                description="Target road segment accessibility set to zero due to active closure."
            )
        else:
            # Step 1: Surrounding Network Detour Congestion Surge
            detour_factor = self.params.rerouting_capacity_factor
            cong_sim = round(min(2.0, base_cong * (1.0 + 0.50 * detour_factor)), 2)
            speed_sim = round(max(5.0, base_speed * (1.0 - 0.30 * detour_factor)), 1)

            sim_state.mobility.congestion_ratio = cong_sim
            sim_state.mobility.forecast_congestion_ratio = cong_sim
            sim_state.mobility.observed_speed = speed_sim
            sim_state.mobility.forecast_speed = speed_sim

            graph.add_step(
                step_number=1,
                name="Detour Network Congestion Redistribution",
                layer_affected="mobility",
                input_variables={"rerouting_capacity_factor": detour_factor, "base_congestion": base_cong},
                output_variables={"simulated_congestion": cong_sim, "simulated_speed": speed_sim},
                method="heuristic_simulation",
                description="Simulated traffic redistribution onto surrounding detour corridors."
            )

        # Step 2: Derived Indicators Update
        sim_state.derived.traffic_congestion_index = sim_state.mobility.congestion_ratio
        sim_state.derived.road_accessibility = sim_state.mobility.road_accessibility

        graph.add_step(
            step_number=2,
            name="Derived Mobility Indicators Synthesis",
            layer_affected="derived",
            input_variables={"mobility_status": sim_state.mobility.status},
            output_variables={"derived_indicators": sim_state.derived.model_dump()},
            method="heuristic_simulation",
            description="Updated derived traffic index and accessibility indicators.",
            depends_on=["Direct Road Segment Closure" if is_directly_closed else "Detour Network Congestion Redistribution"]
        )

        sim_state.provenance.is_synthetic = True
        sim_state.provenance.data_provenance_status = "scenario_simulation"
        sim_state.provenance.scientific_validation_warning = HEURISTIC_WARNING
        if "road_closure_scenario" not in sim_state.provenance.sources:
            sim_state.provenance.sources.append("road_closure_scenario")

        return sim_state, graph.get_steps()


class AirPollutionScenario(BaseScenario):
    """
    Air Pollution Event Scenario.
    Propagates: Pollutant Concentration -> AQI Sub-index -> Air Quality Category -> Derived Indicators
    """
    scenario_type = "air_pollution"
    scenario_name = "Air Pollution Event Scenario"

    def __init__(self, params: AirPollutionParams):
        self.params = params

    def apply(self, base_state: CityState) -> Tuple[CityState, List[TransformationStep]]:
        state_dict = copy.deepcopy(base_state.model_dump())
        sim_state = CityState(**state_dict)

        graph = DependencyGraph()

        if not self.is_in_scope(sim_state, self.params.spatial_scope):
            return sim_state, []

        pollutant_name = self.params.pollutant
        base_val = getattr(sim_state.environment, pollutant_name, None) or 20.0

        sim_val = round(base_val * self.params.multiplier + self.params.delta, 2)
        setattr(sim_state.environment, pollutant_name, sim_val)

        # Recalculate AQI roughly from PM2.5 or primary pollutant
        base_aqi = sim_state.environment.aqi_value or 50
        aqi_sim = int(round(base_aqi * self.params.multiplier + (self.params.delta * 2.0)))
        sim_state.environment.aqi_value = aqi_sim

        if aqi_sim <= 50:
            aqi_cat = "GOOD"
        elif aqi_sim <= 100:
            aqi_cat = "MODERATE"
        elif aqi_sim <= 200:
            aqi_cat = "UNHEALTHY"
        elif aqi_sim <= 300:
            aqi_cat = "VERY_UNHEALTHY"
        else:
            aqi_cat = "HAZARDOUS"

        sim_state.environment.air_quality_category = aqi_cat
        sim_state.derived.air_quality_category = aqi_cat

        graph.add_step(
            step_number=1,
            name="Air Pollutant Emission Surge",
            layer_affected="environment",
            input_variables={"pollutant": pollutant_name, "multiplier": self.params.multiplier, "delta": self.params.delta},
            output_variables={"simulated_pollutant_val": sim_val, "simulated_aqi": aqi_sim, "air_quality_category": aqi_cat},
            method="linear_perturbation",
            description="Perturbed targeted atmospheric pollutant concentration and recalculated AQI sub-index category."
        )

        sim_state.provenance.is_synthetic = True
        sim_state.provenance.data_provenance_status = "scenario_simulation"
        sim_state.provenance.scientific_validation_warning = HEURISTIC_WARNING
        if "air_pollution_scenario" not in sim_state.provenance.sources:
            sim_state.provenance.sources.append("air_pollution_scenario")

        return sim_state, graph.get_steps()


class EmergencyDemandScenario(BaseScenario):
    """
    Emergency Demand Surge Scenario.
    Prepares architecture for Phase 13 Emergency Resource Optimization.
    """
    scenario_type = "emergency_demand"
    scenario_name = "Emergency Demand Surge Scenario"

    def __init__(self, params: EmergencyDemandParams):
        self.params = params

    def apply(self, base_state: CityState) -> Tuple[CityState, List[TransformationStep]]:
        state_dict = copy.deepcopy(base_state.model_dump())
        sim_state = CityState(**state_dict)

        graph = DependencyGraph()

        if not self.is_in_scope(sim_state, self.params.spatial_scope):
            return sim_state, []

        base_density = sim_state.infrastructure.emergency_service_density or 1.0
        sim_density = round(base_density * self.params.hospital_demand_multiplier + self.params.incident_count_surge * 0.1, 3)

        sim_state.infrastructure.emergency_service_density = sim_density
        sim_state.derived.emergency_service_density = sim_density

        graph.add_step(
            step_number=1,
            name="Emergency Demand Surge Propagation",
            layer_affected="infrastructure",
            input_variables={"demand_multiplier": self.params.hospital_demand_multiplier, "incident_surge": self.params.incident_count_surge},
            output_variables={"emergency_service_density": sim_density},
            method="heuristic_simulation",
            description="Simulated hospital demand surge and emergency service stress."
        )

        sim_state.provenance.is_synthetic = True
        sim_state.provenance.data_provenance_status = "scenario_simulation"
        sim_state.provenance.scientific_validation_warning = HEURISTIC_WARNING
        if "emergency_demand_scenario" not in sim_state.provenance.sources:
            sim_state.provenance.sources.append("emergency_demand_scenario")

        return sim_state, graph.get_steps()
