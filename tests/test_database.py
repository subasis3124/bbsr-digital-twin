import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app import models

def test_database_config():
    """
    Verifies that configurations load correctly and assemble the database URL.
    """
    assert settings.POSTGRES_DB == "bbsr_digital_twin"
    assert settings.POSTGRES_USER == "postgres"
    assert "postgresql://" in settings.database_url

def test_sqlalchemy_model_structures():
    """
    Verifies that SQLAlchemy ORM classes are defined with the correct attributes
    and relationship bindings.
    """
    # 1. City model structure
    assert hasattr(models.City, "id")
    assert hasattr(models.City, "name")
    assert hasattr(models.City, "geom")

    # 2. Ward model structure
    assert hasattr(models.Ward, "ward_number")
    assert hasattr(models.Ward, "geom")

    # 3. Roads and Traffic relationship
    assert hasattr(models.Road, "traffic_observations")
    assert hasattr(models.Traffic, "road")

    # 4. Spatial grid cell relationships
    assert hasattr(models.SpatialGridCell, "satellite_features")
    assert hasattr(models.SpatialGridCell, "predictions")
    assert hasattr(models.SpatialGridCell, "simulations")

def test_database_connection_optional():
    """
    Tries to connect to the actual PostgreSQL database container if running,
    otherwise catches the operational error and skips gracefully.
    """
    try:
        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 1})
        conn = engine.connect()
        conn.close()
        database_available = True
    except Exception:
        database_available = False

    if not database_available:
        pytest.skip("PostgreSQL database container is not running or unreachable. Skipping live connection tests.")
