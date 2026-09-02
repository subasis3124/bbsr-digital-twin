from typing import List, Dict, Any, Optional
from ml.city_state.schema import CityState
from ml.simulation.schemas import ImpactSummary, MetricDelta

class SimulationImpactAnalyzer:
    """
    Analyzes and calculates defensible, structured impact metrics between a BASE City State
    and a SIMULATED City State representation.
    """

    @classmethod
    def analyze(
        self,
        base_states: List[CityState],
        simulated_states: List[CityState],
        directly_simulated_fields: List[str] = None
    ) -> ImpactSummary:
        if not base_states or not simulated_states or len(base_states) != len(simulated_states):
            return ImpactSummary(
                affected_spatial_units_count=0,
                total_affected_population=0,
                affected_hospitals_count=0,
                affected_schools_count=0,
                overall_severity="LOW",
                metrics={},
                spatial_unit_deltas=[]
            )

        directly_simulated_fields = directly_simulated_fields or []

        spatial_unit_deltas = []
        tot_affected_pop = 0
        tot_hospitals = 0
        tot_schools = 0

        # Aggregation collectors
        base_speeds, sim_speeds = [], []
        base_congestions, sim_congestions = [], []
        base_floods, sim_floods = [], []
        base_aqis, sim_aqis = [], []
        base_accessibilities, sim_accessibilities = [], []
        base_rainfalls, sim_rainfalls = [], []

        affected_units_count = 0

        for b, s in zip(base_states, simulated_states):
            b_dict = b.model_dump() if hasattr(b, "model_dump") else b
            s_dict = s.model_dump() if hasattr(s, "model_dump") else s

            spatial_id = b_dict["location"]["spatial_id"]
            pop_cnt = b_dict["population"].get("population_count") or 0
            hosp_cnt = b_dict["infrastructure"].get("hospitals_count") or 0
            sch_cnt = b_dict["infrastructure"].get("schools_count") or 0

            # Direct vs derived deltas for this unit
            b_speed = b_dict["mobility"].get("observed_speed")
            s_speed = s_dict["mobility"].get("observed_speed")
            b_cong = b_dict["derived"].get("traffic_congestion_index")
            s_cong = s_dict["derived"].get("traffic_congestion_index")
            b_flood = b_dict["hazards"].get("flood_risk_probability")
            s_flood = s_dict["hazards"].get("flood_risk_probability")
            b_aqi = b_dict["environment"].get("aqi_value")
            s_aqi = s_dict["environment"].get("aqi_value")
            b_acc = b_dict["mobility"].get("road_accessibility")
            s_acc = s_dict["mobility"].get("road_accessibility")
            b_rain = b_dict["environment"].get("rainfall")
            s_rain = s_dict["environment"].get("rainfall")

            # Check if this spatial unit was perturbed/impacted
            is_impacted = False
            if s_speed != b_speed or s_flood != b_flood or s_aqi != b_aqi or s_rain != b_rain or s_acc != b_acc:
                is_impacted = True
                affected_units_count += 1
                tot_affected_pop += pop_cnt
                tot_hospitals += hosp_cnt
                tot_schools += sch_cnt

            if b_speed is not None and s_speed is not None:
                base_speeds.append(b_speed)
                sim_speeds.append(s_speed)
            if b_cong is not None and s_cong is not None:
                base_congestions.append(b_cong)
                sim_congestions.append(s_cong)
            if b_flood is not None and s_flood is not None:
                base_floods.append(b_flood)
                sim_floods.append(s_flood)
            if b_aqi is not None and s_aqi is not None:
                base_aqis.append(b_aqi)
                sim_aqis.append(s_aqi)
            if b_acc is not None and s_acc is not None:
                base_accessibilities.append(b_acc)
                sim_accessibilities.append(s_acc)
            if b_rain is not None and s_rain is not None:
                base_rainfalls.append(b_rain)
                sim_rainfalls.append(s_rain)

            spatial_unit_deltas.append({
                "spatial_id": spatial_id,
                "is_impacted": is_impacted,
                "speed_delta_kmh": round(s_speed - b_speed, 2) if (b_speed is not None and s_speed is not None) else 0.0,
                "flood_risk_delta": round(s_flood - b_flood, 4) if (b_flood is not None and s_flood is not None) else 0.0,
                "aqi_delta": (s_aqi - b_aqi) if (b_aqi is not None and s_aqi is not None) else 0,
                "accessibility_delta": round(s_acc - b_acc, 2) if (b_acc is not None and s_acc is not None) else 0.0
            })

        # Calculate macro metrics
        metrics: Dict[str, MetricDelta] = {}

        def build_metric(key: str, base_arr, sim_arr, unit: str, default_cat: str = "DERIVED") -> MetricDelta:
            cat = "DIRECTLY_SIMULATED" if key in directly_simulated_fields else default_cat
            if not base_arr or not sim_arr:
                return MetricDelta(metric_name=key, category="UNAVAILABLE", unit=unit)
            avg_base = sum(base_arr) / len(base_arr)
            avg_sim = sum(sim_arr) / len(sim_arr)
            delta_abs = avg_sim - avg_base
            delta_pct = (delta_abs / avg_base * 100.0) if avg_base != 0 else 0.0
            return MetricDelta(
                metric_name=key,
                base_value=round(avg_base, 2),
                simulated_value=round(avg_sim, 2),
                delta_absolute=round(delta_abs, 2),
                delta_percentage=round(delta_pct, 2),
                category=cat,
                unit=unit
            )

        metrics["traffic_speed"] = build_metric("traffic_speed", base_speeds, sim_speeds, "km/h")
        metrics["congestion_index"] = build_metric("congestion_index", base_congestions, sim_congestions, "ratio")
        metrics["flood_risk_probability"] = build_metric("flood_risk_probability", base_floods, sim_floods, "probability")
        metrics["air_quality_index"] = build_metric("air_quality_index", base_aqis, sim_aqis, "AQI")
        metrics["road_accessibility"] = build_metric("road_accessibility", base_accessibilities, sim_accessibilities, "ratio")
        metrics["rainfall"] = build_metric("rainfall", base_rainfalls, sim_rainfalls, "mm")

        # Determine overall severity
        max_flood = max(sim_floods) if sim_floods else 0.0
        avg_speed_drop_pct = abs(metrics["traffic_speed"].delta_percentage or 0.0) if (metrics["traffic_speed"].delta_absolute or 0.0) < 0 else 0.0

        if max_flood > 0.75 or avg_speed_drop_pct > 50.0:
            severity = "CRITICAL"
        elif max_flood > 0.50 or avg_speed_drop_pct > 25.0:
            severity = "HIGH"
        elif max_flood > 0.25 or avg_speed_drop_pct > 10.0:
            severity = "MODERATE"
        else:
            severity = "LOW"

        return ImpactSummary(
            affected_spatial_units_count=affected_units_count,
            total_affected_population=tot_affected_pop,
            affected_hospitals_count=tot_hospitals,
            affected_schools_count=tot_schools,
            overall_severity=severity,
            metrics=metrics,
            spatial_unit_deltas=spatial_unit_deltas
        )
