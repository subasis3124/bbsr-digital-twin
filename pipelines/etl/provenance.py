import time
import uuid
from datetime import datetime, timezone

class JobContext:
    def __init__(self, source: str, dataset: str):
        self.source = source
        self.dataset = dataset
        self.job_uuid = str(uuid.uuid4())
        self.start_time = time.time()
        self.execution_timestamp = datetime.now(timezone.utc)
        self.period_start = None
        self.period_end = None
        
        self.records_processed = 0
        self.records_inserted = 0
        self.records_updated = 0
        self.records_skipped = 0
        self.records_rejected = 0
        
        self.status = "success"
        self.error_message = None
        self.duration = 0.0

    def start(self, period_start=None, period_end=None):
        self.start_time = time.time()
        self.period_start = period_start
        self.period_end = period_end

    def end(self, status="success", error_message=None):
        self.duration = time.time() - self.start_time
        self.status = status
        self.error_message = error_message[:1000] if error_message else None

    def to_dict(self):
        return {
            "source": self.source,
            "dataset": self.dataset,
            "job_uuid": self.job_uuid,
            "execution_time": self.execution_timestamp,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "status": self.status,
            "records_processed": self.records_processed,
            "records_inserted": self.records_inserted,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_rejected": self.records_rejected,
            "error_message": self.error_message,
            "duration": self.duration
        }
