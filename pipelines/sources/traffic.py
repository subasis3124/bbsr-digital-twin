import os
from datetime import datetime, timedelta, timezone
import numpy as np

from pipelines.etl.base import BaseETLPipeline
from backend.app.models import Road, Traffic

class TrafficObservationsPipeline(BaseETLPipeline):
    """
    ETL source pipeline for generating synthetic traffic histories when no real-world feeds exist.
    Stores observations with the source labeled 'synthetic_simulator'.
    """
    
    def __init__(self):
        super().__init__("traffic", "hourly_observations")

    def discover(self, context, db, **kwargs):
        road_count = db.query(Road).count()
        self.logger.info(f"Discovered {road_count} total roads in database.")
        context.file_size = road_count

    def download(self, context, db, **kwargs):
        pass

    def validate(self, context, db, **kwargs) -> bool:
        return True

    def transform(self, context, db, **kwargs) -> list:
        # Generate synthetic hourly observations for the first 100 roads in database
        roads = db.query(Road).order_by(Road.id).limit(100).all()
        if not roads:
            self.logger.warning("No roads found in database. Cannot extract traffic observations.")
            return []

        # Fix random seed for replicable data generation across runs
        np.random.seed(42)

        transformed = []
        end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=7)

        current_time = start_time
        while current_time <= end_time:
            hour = current_time.hour
            day_of_week = current_time.weekday()
            is_weekend = day_of_week >= 5

            # Rush hour factor definitions
            if (8 <= hour <= 10) or (17 <= hour <= 19):
                speed_multiplier = 0.55 if not is_weekend else 0.8
                congestion_base = 0.75 if not is_weekend else 0.35
            elif 22 <= hour or hour <= 5:
                speed_multiplier = 1.15
                congestion_base = 0.05
            else:
                speed_multiplier = 0.9
                congestion_base = 0.25

            for road in roads:
                base_speed = road.maxspeed or 40
                
                # Introduce slight variation
                noise_speed = float(np.random.normal(0, 2))
                noise_congestion = float(np.random.normal(0, 0.05))

                speed = max(5, min(120, int(base_speed * speed_multiplier + noise_speed)))
                congestion = max(0.0, min(1.0, float(congestion_base + noise_congestion)))

                transformed.append({
                    "timestamp": current_time,
                    "road_id": road.id,
                    "observed_speed": speed,
                    "congestion_ratio": congestion,
                    "source": "synthetic_simulator"
                })
            current_time += timedelta(hours=1)

        context.records_processed = len(transformed)
        return transformed

    def load(self, context, db, transformed_data, **kwargs):
        if not transformed_data:
            self.logger.info("Transform returned empty list. No database writes executed.")
            context.records_inserted = 0
            context.records_updated = 0
            return

        self.logger.info(f"Ingesting {len(transformed_data)} synthetic observations into database...")
        
        # Clear existing observations to ensure idempotency across script runs
        db.query(Traffic).delete()
        db.commit()

        # Perform bulk database insert for high throughput
        records = [Traffic(**item) for item in transformed_data]
        db.bulk_save_objects(records)
        db.commit()

        context.records_inserted = len(transformed_data)
        context.records_updated = 0

    def verify(self, context, db, **kwargs):
        count = db.query(Traffic).count()
        self.logger.info(f"Verified target: {count} total rows in traffic table.")
