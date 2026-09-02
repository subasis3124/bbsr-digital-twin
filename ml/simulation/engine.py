from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timezone
import uuid
import json
import copy
from sqlalchemy.orm import Session

from backend.app import models
from ml.city_state import CityStateAggregator, CityStateValidator
from ml.city_state.schema import CityState
from ml.simulation.schemas import (
    SimulationScenario, SpatialScope, HeavyRainfallParams,
    RoadClosureParams, AirPollutionParams, EmergencyDemandParams,
    SimulationResult, TransformationStep
)
from ml.simulation.scenarios import (
    HeavyRainfallScenario, RoadClosureScenario, AirPollutionScenario,
    EmergencyDemandScenario, BaseScenario, HEURISTIC_WARNING
)
from ml.simulation.impact import SimulationImpactAnalyzer

class WhatIfSimulationEngine:
    """
    Unified What-If Simulation Engine.
    Executes counterfactual urban scenarios on base city states to produce reproducible,
    explainable simulated states and structured impact metrics.
    """

    ENGINE_VERSION = "1.0.0"

    def __init__(self, db: Session = None):
        self.db = db

    def run_simulation(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
        base_states: Optional[List[CityState]] = None,
        base_timestamp: Optional[datetime] = None,
        simulation_timestamp: Optional[datetime] = None,
        spatial_scope: Optional[Dict[str, Any]] = None,
        save: bool = False
    ) -> SimulationResult:
        """
        Runs a What-If simulation given a scenario type, strongly-typed parameters,
        and base city states. Returns a SimulationResult.
        """
        now_utc = datetime.now(timezone.utc)
        ts_base = base_timestamp or now_utc
        ts_sim = simulation_timestamp or ts_base

        if ts_sim < ts_base:
            raise ValueError("Simulation timestamp cannot precede base state timestamp (temporal leakage risk).")

        # 1. Parse and validate spatial scope
        scope_obj = SpatialScope(**(spatial_scope or {}))

        # 2. Instantiate and validate scenario object
        scenario_instance, typed_params = self._create_scenario(scenario_type, parameters, scope_obj)

        # 3. Load or generate base states if not explicitly provided
        if not base_states:
            if not self.db:
                raise ValueError("Database session required when base_states are not explicitly provided.")
            base_states = self._load_base_states(scope_obj, ts_base)

        if not base_states:
            raise ValueError("No base city states found for specified spatial scope and timestamp.")

        # 4. Execute simulation across base states (preserving base state immutability)
        simulated_states: List[CityState] = []
        all_transformations: List[TransformationStep] = []
        directly_simulated_fields = []

        if scenario_type == "heavy_rainfall":
            directly_simulated_fields = ["rainfall"]
        elif scenario_type == "road_closure":
            directly_simulated_fields = ["road_accessibility", "traffic_speed"]
        elif scenario_type == "air_pollution":
            directly_simulated_fields = ["air_quality_index"]

        for b_state in base_states:
            sim_state, steps = scenario_instance.apply(b_state)
            simulated_states.append(sim_state)
            if steps and not all_transformations:
                all_transformations = steps

        # 5. Perform Impact Analysis
        impact_summary = SimulationImpactAnalyzer.analyze(
            base_states=base_states,
            simulated_states=simulated_states,
            directly_simulated_fields=directly_simulated_fields
        )

        # 6. Build Scenario Metadata
        scenario_meta = SimulationScenario(
            scenario_id=str(uuid.uuid4()),
            scenario_type=scenario_type,
            scenario_name=scenario_instance.scenario_name,
            base_state_timestamp=ts_base.isoformat(),
            simulation_timestamp=ts_sim.isoformat(),
            spatial_scope=scope_obj,
            parameters=parameters,
            assumptions=[
                "Scenario transformations apply heuristic propagation graphs.",
                "Original baseline state remains strictly immutable.",
                "Spatial topology and static infrastructure constraints are preserved."
            ],
            generated_at=now_utc.isoformat(),
            engine_version=self.ENGINE_VERSION
        )

        provenance_dict = {
            "simulation_id": scenario_meta.scenario_id,
            "scenario_type": scenario_type,
            "engine_version": self.ENGINE_VERSION,
            "is_synthetic": True,
            "data_provenance_status": "scenario_simulation",
            "scientific_validation_warning": HEURISTIC_WARNING,
            "generated_at": now_utc.isoformat(),
            "assumptions": scenario_meta.assumptions
        }

        result = SimulationResult(
            scenario=scenario_meta,
            base_states=[s.model_dump() for s in base_states],
            simulated_states=[s.model_dump() for s in simulated_states],
            impact_summary=impact_summary,
            transformations=all_transformations,
            provenance=provenance_dict
        )

        # 7. Persist to DB if requested
        if save and self.db:
            self._persist_simulation_run(result, ts_base, ts_sim, scope_obj.scope_type)

        return result

    def _create_scenario(self, scenario_type: str, parameters: Dict[str, Any], scope: SpatialScope) -> Tuple[BaseScenario, Any]:
        params_copy = copy.deepcopy(parameters or {})
        params_copy["spatial_scope"] = scope.model_dump()

        if scenario_type == "heavy_rainfall":
            typed = HeavyRainfallParams(**params_copy)
            return HeavyRainfallScenario(typed), typed
        elif scenario_type == "road_closure":
            typed = RoadClosureParams(**params_copy)
            return RoadClosureScenario(typed), typed
        elif scenario_type == "air_pollution":
            typed = AirPollutionParams(**params_copy)
            return AirPollutionScenario(typed), typed
        elif scenario_type == "emergency_demand":
            typed = EmergencyDemandParams(**params_copy)
            return EmergencyDemandScenario(typed), typed
        else:
            raise ValueError(f"Unsupported scenario_type '{scenario_type}'. Supported types: heavy_rainfall, road_closure, air_pollution, emergency_demand")

    def _load_base_states(self, scope: SpatialScope, ts_base: datetime) -> List[CityState]:
        aggregator = CityStateAggregator(self.db)
        states = []

        grid_cells_query = self.db.query(models.SpatialGridCell)
        if scope.cell_codes:
            grid_cells_query = grid_cells_query.filter(models.SpatialGridCell.cell_code.in_(scope.cell_codes))
        elif scope.scope_type == "grid_cell":
            grid_cells_query = grid_cells_query.limit(50)
        else:
            grid_cells_query = grid_cells_query.limit(20)

        cells = grid_cells_query.all()
        for cell in cells:
            st = aggregator.aggregate_grid_cell(cell, state_timestamp=ts_base)
            states.append(st)

        if not states:
            # Fallback for unpopulated database or mock testing sessions
            from ml.city_state import (
                SpatialIdentity, TemporalIdentity, MobilityState, EnvironmentalState,
                HazardState, PopulationContext, InfrastructureContext, ProvenanceMetadata, DerivedIndicators
            )
            fallback_state = CityState(
                location=SpatialIdentity(spatial_unit_type="grid_cell", spatial_id="SYN_CELL_001", cell_code="SYN_CELL_001", centroid=[85.83, 20.27]),
                time=TemporalIdentity(state_timestamp=ts_base.isoformat(), target_timestamp=ts_base.isoformat(), state_type="CURRENT"),
                mobility=MobilityState(observed_speed=40.0, congestion_ratio=0.2, road_accessibility=1.0),
                environment=EnvironmentalState(pm25=15.0, aqi_value=45, air_quality_category="GOOD", rainfall=0.0),
                hazards=HazardState(flood_risk_probability=0.10, flood_risk_level="LOW"),
                population=PopulationContext(population_count=500),
                infrastructure=InfrastructureContext(hospitals_count=1, schools_count=2, emergency_service_density=1.0),
                provenance=ProvenanceMetadata(sources=["synthetic_fallback"], is_synthetic=True, generated_at=ts_base.isoformat()),
                derived=DerivedIndicators(traffic_congestion_index=0.2, flood_risk_level="LOW", air_quality_category="GOOD", rainfall_intensity="NONE", road_accessibility=1.0)
            )
            states.append(fallback_state)

        return states

    def _persist_simulation_run(self, result: SimulationResult, ts_base: datetime, ts_sim: datetime, scope_type: str):
        sim_run = models.SimulationRun(
            simulation_id=result.scenario.scenario_id,
            scenario_type=result.scenario.scenario_type,
            scenario_name=result.scenario.scenario_name,
            base_state_timestamp=ts_base,
            simulation_timestamp=ts_sim,
            spatial_scope_type=scope_type,
            engine_version=self.ENGINE_VERSION,
            is_synthetic=True,
            parameters=result.scenario.parameters,
            impact_summary=result.impact_summary.model_dump(),
            provenance=result.provenance,
            transformations=[t.model_dump() for t in result.transformations],
            base_state_count=len(result.base_states),
            simulated_state_count=len(result.simulated_states),
            simulated_states_payload=result.simulated_states
        )
        self.db.add(sim_run)
        self.db.commit()
        self.db.refresh(sim_run)
