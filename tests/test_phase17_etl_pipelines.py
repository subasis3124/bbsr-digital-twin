import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from pipelines.etl.provenance import JobContext
from pipelines.sources.traffic import TrafficObservationsPipeline
from pipelines.sources.air_quality import AirQualityPipeline
from pipelines.sources.open_meteo import OpenMeteoPipeline


# 1. Pipeline Idempotency & Repeated Execution Test
def test_traffic_pipeline_idempotency():
    """
    Verifies that running the traffic ETL pipeline repeatedly clears previous state or operates idempotently
    without producing uncontrolled duplicates.
    """
    pipeline = TrafficObservationsPipeline()
    context = JobContext("traffic", "hourly_observations")

    mock_road = MagicMock()
    mock_road.id = 1
    mock_road.maxspeed = 50

    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 1
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_road]

    # RUN 1
    transformed_1 = pipeline.transform(context, mock_db)
    pipeline.load(context, mock_db, transformed_1)
    
    # RUN 2 (repeated execution)
    transformed_2 = pipeline.transform(context, mock_db)
    pipeline.load(context, mock_db, transformed_2)

    # Verify delete was called before bulk save for idempotency
    assert mock_db.query.return_value.delete.call_count >= 2
    assert len(transformed_1) == len(transformed_2)


# 2. Pipeline Failure Recovery & Graceful Handling
def test_open_meteo_pipeline_network_failure(caplog):
    """
    Simulates network timeout/failure during source download and verifies graceful logging/handling.
    """
    pipeline = OpenMeteoPipeline()
    context = JobContext("weather", "open-meteo")

    mock_db = MagicMock()

    with patch("requests.get", side_effect=Exception("Connection Timeout to OpenMeteo API")):
        results = pipeline.transform(context, mock_db, backfill_days=1)
        
    assert results == []


def test_air_quality_pipeline_malformed_response():
    """
    Simulates malformed json response missing expected fields and verifies no crash.
    """
    pipeline = AirQualityPipeline()
    context = JobContext("air_quality", "openaq-cpcb")

    mock_response = MagicMock()
    mock_response.json.return_value = {"hourly": {}}  # missing time & pm2_5 keys

    with patch("requests.get", return_value=mock_response):
        results = pipeline._transform_open_meteo_aq(context)

    assert results == []


# 3. Synthetic Data Labeling Verification
def test_etl_synthetic_data_provenance_labeling():
    """
    Ensures that all generated synthetic records are properly labeled with synthetic source metadata.
    """
    traffic_pipe = TrafficObservationsPipeline()
    context = JobContext("traffic", "hourly_observations")

    mock_road = MagicMock()
    mock_road.id = 10
    mock_road.maxspeed = 40

    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_road]

    records = traffic_pipe.transform(context, mock_db)
    assert len(records) > 0
    assert all(r["source"] == "synthetic_simulator" for r in records)
