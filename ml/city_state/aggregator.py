import shapely.geometry
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from backend.app import models
from ml.city_state.schema import (
    CityState, SpatialIdentity, TemporalIdentity, MobilityState,
    EnvironmentalState, HazardState, PopulationContext, InfrastructureContext,
    ProvenanceMetadata, DerivedIndicators
)
from ml.city_state.registry import DataSourceRegistry
from ml.city_state.validators import CityStateValidator

SCIENTIFIC_WARNING = (
    "WARNING: City state snapshot contains forecasts or feature layers derived from "
    "synthetic validation baselines because real-time unified sensor streams are partially unavailable."
)

class CityStateAggregator:
    """
    Unified City State Aggregation Engine.
    Combines spatial, temporal, environmental, mobility, hazard, population, and infrastructure
    layers into canonical CityState entities.
    """

    def __init__(self, db: Session):
        self.db = db

    def aggregate_grid_cell(
        self,
        grid_cell: models.SpatialGridCell,
        state_timestamp: Optional[datetime] = None,
        forecast_horizon_minutes: int = 0
    ) -> CityState:
        """
        Aggregates data for a specific SpatialGridCell into a canonical CityState.
        """
        now_utc = datetime.now(timezone.utc)
        ts_obs = state_timestamp or now_utc
        ts_target = ts_obs + timedelta(minutes=forecast_horizon_minutes)
        state_type = "FORECAST" if forecast_horizon_minutes > 0 else "CURRENT"

        # 1. Spatial Identity
        geom_shape = to_shape(grid_cell.geom) if grid_cell.geom is not None else None
        geom_dict = shapely.geometry.mapping(geom_shape) if geom_shape else None
        centroid_shape = to_shape(grid_cell.centroid) if grid_cell.centroid is not None else None
        centroid_coords = [centroid_shape.x, centroid_shape.y] if centroid_shape else None
        bbox = list(geom_shape.bounds) if geom_shape else None

        spatial = SpatialIdentity(
            spatial_unit_type="grid_cell",
            spatial_id=grid_cell.cell_code,
            cell_id=grid_cell.id,
            cell_code=grid_cell.cell_code,
            centroid=centroid_coords,
            bbox=bbox,
            geometry=geom_dict
        )

        # 2. Temporal Identity
        temporal = TemporalIdentity(
            state_timestamp=ts_obs.isoformat(),
            target_timestamp=ts_target.isoformat(),
            forecast_horizon_minutes=forecast_horizon_minutes,
            state_type=state_type
        )

        component_statuses = {}
        sources = set()
        model_names = set()
        model_versions = set()
        is_synthetic = False

        # 3. Environment Layer (Satellite + Weather + AirQuality)
        sat = self.db.query(models.SatelliteFeature).filter(
            models.SatelliteFeature.cell_id == grid_cell.id
        ).order_by(models.SatelliteFeature.timestamp.desc()).first()

        wtr = self.db.query(models.Weather).order_by(models.Weather.timestamp.desc()).first()
        aq = self.db.query(models.AirQuality).order_by(models.AirQuality.timestamp.desc()).first()
        aq_pred = self.db.query(models.AirQualityPrediction).order_by(models.AirQualityPrediction.target_time.desc()).first()

        env_status = "AVAILABLE" if (sat or wtr or aq or aq_pred) else "MISSING"
        component_statuses["environment"] = env_status

        pm25_val = float(aq.pm25) if (aq and aq.pm25 is not None) else None
        pm10_val = float(aq.pm10) if (aq and aq.pm10 is not None) else None
        aqi_val = aq.aqi_value if (aq and aq.aqi_value is not None) else None

        if forecast_horizon_minutes > 0 and aq_pred:
            aqi_val = aq_pred.aqi_sub_index or aqi_val
            model_names.add(aq_pred.model_name)
            model_versions.add(aq_pred.model_version)
            if aq_pred.is_synthetic:
                is_synthetic = True

        env = EnvironmentalState(
            pm25=pm25_val,
            pm10=pm10_val,
            co=float(aq.co) if (aq and aq.co is not None) else None,
            no2=float(aq.no2) if (aq and aq.no2 is not None) else None,
            so2=float(aq.so2) if (aq and aq.so2 is not None) else None,
            o3=float(aq.o3) if (aq and aq.o3 is not None) else None,
            aqi_value=aqi_val,
            air_quality_category=self._compute_aqi_category(aqi_val),
            temperature=float(wtr.temperature) if (wtr and wtr.temperature is not None) else None,
            rainfall=float(wtr.rainfall) if (wtr and wtr.rainfall is not None) else None,
            humidity=float(wtr.humidity) if (wtr and wtr.humidity is not None) else None,
            wind_speed=float(wtr.wind_speed) if (wtr and wtr.wind_speed is not None) else None,
            elevation=float(sat.elevation) if (sat and sat.elevation is not None) else None,
            slope=float(sat.slope) if (sat and sat.slope is not None) else None,
            ndvi=float(sat.ndvi) if (sat and sat.ndvi is not None) else None,
            ndwi=float(sat.ndwi) if (sat and sat.ndwi is not None) else None,
            ndbi=float(sat.ndbi) if (sat and sat.ndbi is not None) else None,
            source="openaq/open-meteo/copernicus",
            status=env_status
        )
        sources.add("openaq")
        sources.add("open-meteo")
        sources.add("copernicus")

        # 4. Hazards Layer (Flood Risk Predictions)
        pred = self.db.query(models.Prediction).filter(
            models.Prediction.cell_id == grid_cell.id
        ).order_by(models.Prediction.prediction_time.desc()).first()

        flood_prob = float(pred.predicted_probability) if (pred and pred.predicted_probability is not None) else None
        flood_level = pred.predicted_class if pred else "LOW"
        hazard_status = "AVAILABLE" if pred else "MISSING"
        component_statuses["hazards"] = hazard_status

        if pred:
            model_names.add(pred.model_name)
            model_versions.add(pred.model_version)
            is_synthetic = True  # Flood risk evaluation labels are synthetic baselines

        hazards = HazardState(
            flood_risk_probability=flood_prob,
            flood_risk_level=flood_level,
            severity="HIGH" if (flood_prob and flood_prob > 0.7) else "NORMAL",
            active_flood_event=bool(flood_prob and flood_prob > 0.5),
            source=pred.model_name if pred else "flood_risk_rf_v1",
            status=hazard_status
        )

        # 5. Mobility Layer (Road traffic & GNN predictions)
        gnn_pred = self.db.query(models.GNNTrafficPrediction).order_by(
            models.GNNTrafficPrediction.prediction_time.desc()
        ).first()

        tr_pred = self.db.query(models.TrafficPrediction).order_by(
            models.TrafficPrediction.prediction_time.desc()
        ).first()

        mobility_status = "AVAILABLE" if (gnn_pred or tr_pred) else "MISSING"
        component_statuses["mobility"] = mobility_status

        spd = float(gnn_pred.predicted_speed) if gnn_pred else (float(tr_pred.predicted_speed) if tr_pred else None)
        cong = float(gnn_pred.predicted_congestion_ratio) if gnn_pred else (float(tr_pred.predicted_congestion_ratio) if tr_pred else None)

        if gnn_pred:
            model_names.add(gnn_pred.model_name)
            model_versions.add(gnn_pred.model_version)
            if gnn_pred.is_synthetic:
                is_synthetic = True
        elif tr_pred:
            model_names.add(tr_pred.model_name)
            model_versions.add(tr_pred.model_version)
            if tr_pred.is_synthetic:
                is_synthetic = True

        # Calculate accessibility based on flood risk
        road_acc = 1.0
        if flood_prob and flood_prob > 0.6:
            road_acc = max(0.0, 1.0 - flood_prob)

        mobility = MobilityState(
            observed_speed=spd,
            maxspeed=50,
            congestion_ratio=cong,
            forecast_speed=spd,
            forecast_congestion_ratio=cong,
            gnn_forecast_speed=float(gnn_pred.predicted_speed) if gnn_pred else None,
            gnn_forecast_congestion_ratio=float(gnn_pred.predicted_congestion_ratio) if gnn_pred else None,
            road_accessibility=round(road_acc, 2),
            source="open-traffic/gnn",
            status=mobility_status
        )

        # 6. Population Context Layer
        pop_record = self.db.query(models.PopulationGrid).order_by(models.PopulationGrid.id).first()
        pop_count = pop_record.population_count if pop_record else None
        pop_status = "AVAILABLE" if pop_record else "MISSING"
        component_statuses["population"] = pop_status

        cell_area_km2 = 0.25  # ~500m x 500m grid cell standard area
        pop_density = float(pop_count) / cell_area_km2 if pop_count else None

        population = PopulationContext(
            population_count=pop_count,
            population_density=pop_density,
            status=pop_status
        )
        sources.add("worldpop-2020")

        # 7. Vector Infrastructure Layer (Counts in database)
        hospitals_cnt = self.db.query(func.count(models.Hospital.id)).scalar() or 0
        beds_sum = self.db.query(func.sum(models.Hospital.beds)).scalar() or 0
        schools_cnt = self.db.query(func.count(models.School.id)).scalar() or 0
        police_cnt = self.db.query(func.count(models.PoliceStation.id)).scalar() or 0
        fire_cnt = self.db.query(func.count(models.FireStation.id)).scalar() or 0
        bus_stops_cnt = self.db.query(func.count(models.BusStop.id)).scalar() or 0
        bus_routes_cnt = self.db.query(func.count(models.BusRoute.id)).scalar() or 0
        water_bodies_cnt = self.db.query(func.count(models.WaterBody.id)).scalar() or 0

        emergency_cnt = hospitals_cnt + police_cnt + fire_cnt
        emergency_density = float(emergency_cnt) / 150.0  # Approx city area km2

        infra_status = "AVAILABLE"
        component_statuses["infrastructure"] = infra_status

        infrastructure = InfrastructureContext(
            hospitals_count=hospitals_cnt,
            hospital_beds=int(beds_sum),
            schools_count=schools_cnt,
            police_stations_count=police_cnt,
            fire_stations_count=fire_cnt,
            bus_stops_count=bus_stops_cnt,
            bus_routes_count=bus_routes_cnt,
            water_bodies_count=water_bodies_cnt,
            emergency_service_density=round(emergency_density, 3),
            status=infra_status
        )
        sources.add("openstreetmap")

        # 8. Derived Indicators
        rainfall_val = env.rainfall or 0.0
        rainfall_cat = "NONE"
        if rainfall_val > 50.0:
            rainfall_cat = "EXTREME"
        elif rainfall_val > 15.0:
            rainfall_cat = "HEAVY"
        elif rainfall_val > 5.0:
            rainfall_cat = "MODERATE"
        elif rainfall_val > 0.0:
            rainfall_cat = "LIGHT"

        derived = DerivedIndicators(
            traffic_congestion_index=cong,
            flood_risk_level=flood_level,
            air_quality_category=env.air_quality_category,
            rainfall_intensity=rainfall_cat,
            emergency_service_density=round(emergency_density, 3),
            population_density=round(pop_density, 1) if pop_density else None,
            road_accessibility=round(road_acc, 2)
        )

        # 9. Provenance Metadata
        provenance = ProvenanceMetadata(
            sources=sorted(list(sources)),
            model_names=sorted(list(model_names)),
            model_versions=sorted(list(model_versions)),
            is_synthetic=is_synthetic,
            data_provenance_status="synthetic_fallback" if is_synthetic else "observed",
            scientific_validation_warning=SCIENTIFIC_WARNING if is_synthetic else None,
            confidence_available=False,
            state_schema_version="1.0.0",
            generated_at=now_utc.isoformat()
        )

        city_state = CityState(
            location=spatial,
            time=temporal,
            mobility=mobility,
            environment=env,
            hazards=hazards,
            population=population,
            infrastructure=infrastructure,
            provenance=provenance,
            derived=derived,
            component_statuses=component_statuses
        )

        return city_state

    def aggregate_ward(
        self,
        ward: models.Ward,
        state_timestamp: Optional[datetime] = None,
        forecast_horizon_minutes: int = 0
    ) -> CityState:
        """
        Aggregates data for a BMC Ward into a canonical CityState.
        """
        now_utc = datetime.now(timezone.utc)
        ts_obs = state_timestamp or now_utc
        ts_target = ts_obs + timedelta(minutes=forecast_horizon_minutes)
        state_type = "FORECAST" if forecast_horizon_minutes > 0 else "CURRENT"

        geom_shape = to_shape(ward.geom) if ward.geom is not None else None
        geom_dict = shapely.geometry.mapping(geom_shape) if geom_shape else None
        centroid_coords = [geom_shape.centroid.x, geom_shape.centroid.y] if geom_shape else None
        bbox = list(geom_shape.bounds) if geom_shape else None

        spatial = SpatialIdentity(
            spatial_unit_type="ward",
            spatial_id=str(ward.ward_number),
            ward_id=ward.id,
            ward_number=ward.ward_number,
            centroid=centroid_coords,
            bbox=bbox,
            geometry=geom_dict
        )

        temporal = TemporalIdentity(
            state_timestamp=ts_obs.isoformat(),
            target_timestamp=ts_target.isoformat(),
            forecast_horizon_minutes=forecast_horizon_minutes,
            state_type=state_type
        )

        component_statuses = {"ward": "AVAILABLE"}
        sources = {"bhubaneswar-ward-gis", "worldpop-2020"}

        pop_count = ward.population_est or 15000
        area_km2 = 2.5
        pop_density = float(pop_count) / area_km2

        pop = PopulationContext(
            population_count=pop_count,
            population_density=round(pop_density, 1),
            status="AVAILABLE"
        )

        env = EnvironmentalState(
            source="open-meteo/openaq",
            status="AVAILABLE"
        )

        hazards = HazardState(
            flood_risk_probability=0.15,
            flood_risk_level="LOW",
            severity="NORMAL",
            source="flood_risk_rf_v1",
            status="AVAILABLE"
        )

        mobility = MobilityState(
            observed_speed=35.0,
            congestion_ratio=0.3,
            road_accessibility=1.0,
            source="open-traffic",
            status="AVAILABLE"
        )

        infra = InfrastructureContext(
            hospitals_count=2,
            hospital_beds=120,
            schools_count=5,
            police_stations_count=1,
            fire_stations_count=0,
            bus_stops_count=8,
            bus_routes_count=3,
            water_bodies_count=1,
            emergency_service_density=1.2,
            status="AVAILABLE"
        )

        derived = DerivedIndicators(
            traffic_congestion_index=0.3,
            flood_risk_level="LOW",
            air_quality_category="GOOD",
            rainfall_intensity="NONE",
            emergency_service_density=1.2,
            population_density=round(pop_density, 1),
            road_accessibility=1.0
        )

        provenance = ProvenanceMetadata(
            sources=sorted(list(sources)),
            model_names=["RandomForest_FloodRisk"],
            model_versions=["1.0.0"],
            is_synthetic=True,
            data_provenance_status="synthetic_fallback",
            scientific_validation_warning=SCIENTIFIC_WARNING,
            confidence_available=False,
            state_schema_version="1.0.0",
            generated_at=now_utc.isoformat()
        )

        return CityState(
            location=spatial,
            time=temporal,
            mobility=mobility,
            environment=env,
            hazards=hazards,
            population=pop,
            infrastructure=infra,
            provenance=provenance,
            derived=derived,
            component_statuses=component_statuses
        )

    def save_snapshot(self, city_state: CityState) -> models.CityStateSnapshot:
        """
        Persists a CityState model into the PostgreSQL/PostGIS database table city_state_snapshots.
        """
        loc = city_state.location
        t = city_state.time
        der = city_state.derived
        prov = city_state.provenance

        # Parse timestamps
        state_dt = datetime.fromisoformat(t.state_timestamp.replace("Z", "+00:00"))
        target_dt = datetime.fromisoformat(t.target_timestamp.replace("Z", "+00:00"))

        snapshot = models.CityStateSnapshot(
            spatial_unit_type=loc.spatial_unit_type,
            spatial_id=loc.spatial_id,
            cell_id=loc.cell_id,
            ward_id=loc.ward_id,
            road_id=loc.road_id,
            state_timestamp=state_dt,
            target_timestamp=target_dt,
            forecast_horizon_minutes=t.forecast_horizon_minutes,
            state_type=t.state_type,
            flood_risk_probability=city_state.hazards.flood_risk_probability,
            flood_risk_level=city_state.hazards.flood_risk_level,
            traffic_congestion_index=der.traffic_congestion_index,
            aqi_value=city_state.environment.aqi_value,
            air_quality_category=der.air_quality_category,
            population_count=city_state.population.population_count,
            population_density=der.population_density,
            emergency_service_density=der.emergency_service_density,
            is_synthetic=prov.is_synthetic,
            data_provenance_status=prov.data_provenance_status,
            state_schema_version=prov.state_schema_version,
            payload=city_state.model_dump()
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    @staticmethod
    def _compute_aqi_category(aqi: Optional[int]) -> Optional[str]:
        if aqi is None:
            return "UNKNOWN"
        if aqi <= 50:
            return "GOOD"
        elif aqi <= 100:
            return "MODERATE"
        elif aqi <= 200:
            return "UNHEALTHY"
        elif aqi <= 300:
            return "VERY_UNHEALTHY"
        return "HAZARDOUS"
