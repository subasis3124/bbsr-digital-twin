from typing import Dict, Any, Optional

class DataSourceRegistry:
    """
    Registry for data sources, models, and freshness metadata contributing to the City State Engine.
    """
    REGISTRY: Dict[str, Dict[str, Any]] = {
        "weather": {
            "source_type": "sensor_api",
            "default_source": "open-meteo",
            "max_freshness_seconds": 10800,  # 3 hours
            "is_synthetic": False,
            "confidence_available": False,
        },
        "air_quality": {
            "source_type": "sensor_api",
            "default_source": "openaq",
            "max_freshness_seconds": 14400,  # 4 hours
            "is_synthetic": False,
            "confidence_available": False,
        },
        "air_quality_forecast": {
            "source_type": "ml_model",
            "default_model": "RandomForest_AQI",
            "version": "1.0.0",
            "is_synthetic": True,
            "confidence_available": False,
            "warning": "WARNING: Air quality forecast model trained on synthetic validation baseline."
        },
        "traffic": {
            "source_type": "sensor_api",
            "default_source": "open-traffic",
            "max_freshness_seconds": 3600,  # 1 hour
            "is_synthetic": False,
            "confidence_available": False,
        },
        "traffic_forecast": {
            "source_type": "ml_model",
            "default_model": "RandomForest_Traffic",
            "version": "1.0.0",
            "is_synthetic": True,
            "confidence_available": False,
            "warning": "WARNING: Traffic forecast model derived from synthetic speed profiles."
        },
        "gnn_traffic_forecast": {
            "source_type": "gnn_model",
            "default_model": "GraphSAGE_GNN",
            "version": "1.0.0",
            "is_synthetic": True,
            "confidence_available": False,
            "warning": "WARNING: GNN traffic forecasting uses spatial graph topology with synthetic validation labels."
        },
        "flood_risk": {
            "source_type": "ml_model",
            "default_model": "RandomForest_FloodRisk",
            "version": "1.0.0",
            "is_synthetic": True,
            "confidence_available": False,
            "warning": "WARNING: Flood risk model evaluated on synthetic hazard labels."
        },
        "population": {
            "source_type": "demographic_dataset",
            "default_source": "worldpop-2020",
            "is_synthetic": False,
            "confidence_available": False,
        },
        "infrastructure": {
            "source_type": "vector_gis",
            "default_source": "openstreetmap",
            "is_synthetic": False,
            "confidence_available": False,
        },
        "satellite": {
            "source_type": "remote_sensing",
            "default_source": "copernicus-sentinel2",
            "is_synthetic": False,
            "confidence_available": False,
        }
    }

    @classmethod
    def get_source_info(cls, key: str) -> Dict[str, Any]:
        return cls.REGISTRY.get(key, {
            "source_type": "unknown",
            "default_source": "unknown",
            "is_synthetic": False,
            "confidence_available": False
        })
