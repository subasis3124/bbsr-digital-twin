import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ml.city_state.schema import CityState

class ValidationResult:
    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, err: str):
        self.is_valid = False
        self.errors.append(err)

    def add_warning(self, warn: str):
        self.warnings.append(warn)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class CityStateValidator:
    """
    Validates a CityState instance for spatial integrity, temporal consistency,
    numeric validity (NaN/Inf checks), and provenance accuracy.
    """

    @classmethod
    def validate(cls, state: CityState) -> ValidationResult:
        result = ValidationResult()

        # 1. Spatial Validation
        loc = state.location
        if not loc.spatial_id:
            result.add_error("Spatial identity 'spatial_id' cannot be empty.")
        if loc.spatial_unit_type not in ["grid_cell", "road", "ward"]:
            result.add_warning(f"Non-standard spatial_unit_type '{loc.spatial_unit_type}'.")

        if loc.centroid:
            lon, lat = loc.centroid[0], loc.centroid[1]
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                result.add_error(f"Invalid centroid coordinates: [{lon}, {lat}].")

        # 2. Temporal Validation
        t = state.time
        try:
            state_dt = datetime.fromisoformat(t.state_timestamp.replace("Z", "+00:00"))
            target_dt = datetime.fromisoformat(t.target_timestamp.replace("Z", "+00:00"))
        except ValueError:
            result.add_error("Invalid ISO timestamp format in temporal identity.")
            state_dt, target_dt = None, None

        if state_dt and target_dt:
            if target_dt < state_dt:
                result.add_error("Target timestamp cannot precede observation state timestamp (temporal leakage risk).")

            if t.state_type == "CURRENT" and t.forecast_horizon_minutes > 0:
                result.add_warning("State type is 'CURRENT' but forecast_horizon_minutes is greater than 0.")
            elif t.state_type == "FORECAST" and t.forecast_horizon_minutes == 0:
                result.add_warning("State type is 'FORECAST' but forecast_horizon_minutes is 0.")

        # 3. Numeric & Range Validation (No NaN / Inf)
        cls._check_numeric_fields(state, result)

        # 4. Provenance & Synthetic Flag Integrity
        prov = state.provenance
        if prov.is_synthetic and not prov.scientific_validation_warning:
            result.add_warning("State marked synthetic but lacks a scientific validation warning message.")

        return result

    @classmethod
    def _check_numeric_fields(cls, state: CityState, result: ValidationResult):
        def check_val(name: str, val: Any, min_val: Optional[float] = None, max_val: Optional[float] = None):
            if val is None:
                return
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    result.add_error(f"Field '{name}' contains invalid numerical value (NaN or Inf).")
                    return
                if min_val is not None and val < min_val:
                    result.add_warning(f"Field '{name}' value {val} is below recommended min bound {min_val}.")
                if max_val is not None and val > max_val:
                    result.add_warning(f"Field '{name}' value {val} is above recommended max bound {max_val}.")

        # Check Hazards
        check_val("hazards.flood_risk_probability", state.hazards.flood_risk_probability, 0.0, 1.0)

        # Check Environment
        check_val("environment.pm25", state.environment.pm25, 0.0, 1000.0)
        check_val("environment.pm10", state.environment.pm10, 0.0, 2000.0)
        check_val("environment.humidity", state.environment.humidity, 0.0, 100.0)
        check_val("environment.ndvi", state.environment.ndvi, -1.0, 1.0)
        check_val("environment.ndwi", state.environment.ndwi, -1.0, 1.0)

        # Check Mobility
        check_val("mobility.observed_speed", state.mobility.observed_speed, 0.0, 200.0)
        check_val("mobility.congestion_ratio", state.mobility.congestion_ratio, 0.0, 2.0)
        check_val("mobility.road_accessibility", state.mobility.road_accessibility, 0.0, 1.0)

        # Check Derived
        check_val("derived.traffic_congestion_index", state.derived.traffic_congestion_index, 0.0, 2.0)
