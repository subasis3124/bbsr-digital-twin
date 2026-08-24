import os
import json
from datetime import datetime, timezone
from shapely.geometry import shape, MultiPolygon, Polygon
from geoalchemy2.shape import from_shape

from pipelines.etl.base import BaseETLPipeline
from backend.app.models import FloodEvent

class FloodTargetPipeline(BaseETLPipeline):
    def __init__(self):
        super().__init__("flood_target", "historical_observations")
        self.default_filepath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "raw", "flood_observations.geojson"
        ))

    def discover(self, context, db, **kwargs):
        filepath = kwargs.get("filepath", self.default_filepath)
        if os.path.exists(filepath):
            self.logger.info(f"Target GeoJSON found at: {filepath}")
            context.file_size = os.path.getsize(filepath)
        else:
            self.logger.warning(f"Target GeoJSON not found at: {filepath}. Empty ingestion will occur.")
            context.file_size = 0

    def download(self, context, db, **kwargs):
        pass

    def validate(self, context, db, **kwargs) -> bool:
        filepath = kwargs.get("filepath", self.default_filepath)
        if not os.path.exists(filepath):
            return True
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "type" not in data or data["type"] != "FeatureCollection":
                self.logger.error("Invalid GeoJSON. Must be a FeatureCollection.")
                return False
            return True
        except Exception as e:
            self.logger.error(f"GeoJSON validation failed: {e}")
            return False

    def transform(self, context, db, **kwargs):
        filepath = kwargs.get("filepath", self.default_filepath)
        if not os.path.exists(filepath):
            return []
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        transformed = []
        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            geom_dict = feature.get("geometry")
            if not geom_dict:
                continue
                
            try:
                geom_shape = shape(geom_dict)
                # Convert Polygon to MultiPolygon if necessary, to match flood_events schema
                if isinstance(geom_shape, Polygon):
                    geom_shape = MultiPolygon([geom_shape])
                    
                if not isinstance(geom_shape, MultiPolygon):
                    self.logger.warning(f"Skipping non-polygon geometry type: {geom_shape.geom_type}")
                    continue
                
                # Extract meta attributes
                event_name = properties.get("event_name", properties.get("name", "Unknown Flood Event"))
                severity = properties.get("severity", "MEDIUM")
                
                # Fetch timestamps
                start_iso = properties.get("start_time", properties.get("date", "2026-01-01T00:00:00Z"))
                try:
                    start_time = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                except ValueError:
                    start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                    
                end_iso = properties.get("end_time")
                end_time = None
                if end_iso:
                    try:
                        end_time = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                
                transformed.append({
                    "event_name": event_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "severity": severity,
                    "geom": geom_shape
                })
            except Exception as e:
                self.logger.warning(f"Failed to transform feature: {e}")
                
        context.records_processed = len(transformed)
        return transformed

    def load(self, context, db, transformed_data, **kwargs):
        if not transformed_data:
            self.logger.info("No records to load.")
            context.records_inserted = 0
            context.records_updated = 0
            return
            
        self.logger.info(f"Loading {len(transformed_data)} flood event polygons into flood_events table...")
        
        # In this target pipeline we append or merge to retain multiple historical events.
        # However, to be idempotent across run retries, we clean existing events with the same event_name.
        inserted = 0
        updated = 0
        
        for item in transformed_data:
            # Check for existing event of the same name and start_time
            existing = db.query(FloodEvent).filter(
                FloodEvent.event_name == item["event_name"],
                FloodEvent.start_time == item["start_time"]
            ).first()
            
            if existing:
                existing.end_time = item["end_time"]
                existing.severity = item["severity"]
                existing.geom = from_shape(item["geom"], srid=4326)
                updated += 1
            else:
                new_event = FloodEvent(
                    event_name=item["event_name"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    severity=item["severity"],
                    geom=from_shape(item["geom"], srid=4326)
                )
                db.add(new_event)
                inserted += 1
                
        db.commit()
        context.records_inserted = inserted
        context.records_updated = updated

    def verify(self, context, db, **kwargs):
        count = db.query(FloodEvent).count()
        self.logger.info(f"Verified {count} records in flood_events table.")
