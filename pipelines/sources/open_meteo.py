import requests
from datetime import datetime, timezone
from pipelines.etl.base import BaseETLPipeline
from pipelines.etl.config import REQUEST_TIMEOUT, DEFAULT_WEATHER_DAYS
from backend.app.models import Weather

class OpenMeteoPipeline(BaseETLPipeline):
    def __init__(self):
        super().__init__("weather", "open-meteo")
        self.latitude = 20.296
        self.longitude = 85.824

    def discover(self, context, db, **kwargs):
        # Check API status
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": "temperature_2m",
            "forecast_days": 1
        }
        res = requests.head(url, params=params, timeout=REQUEST_TIMEOUT)
        if res.status_code != 200:
            raise ConnectionError(f"Open-Meteo forecast API head request failed with status: {res.status_code}")
        self.logger.info("Open-Meteo weather service discovered.")

    def download(self, context, db, **kwargs):
        # We query the API in the transform step since it is a JSON API
        pass

    def validate(self, context, db, **kwargs) -> bool:
        return True

    def transform(self, context, db, **kwargs):
        # Query Open-Meteo for past_days and forecast
        backfill_days = kwargs.get("backfill_days", DEFAULT_WEATHER_DAYS)
        self.logger.info(f"Fetching weather archive and forecasting data for lat={self.latitude}, lon={self.longitude} (backfill_days={backfill_days})...")
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "past_days": backfill_days,
            "forecast_days": 3  # Fetch 3 days ahead as forecast
        }
        
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        precip = hourly.get("precipitation", [])
        winds = hourly.get("wind_speed_10m", [])
        
        results = []
        now_utc = datetime.now(timezone.utc)
        
        for i in range(len(times)):
            # Convert ISO8601 string (e.g. 2026-08-23T00:00) to datetime
            dt = datetime.fromisoformat(times[i]).replace(tzinfo=timezone.utc)
            is_forecast = dt > now_utc
            
            results.append({
                "timestamp": dt,
                "temperature": float(temps[i]) if temps[i] is not None else None,
                "rainfall": float(precip[i]) if precip[i] is not None else None,
                "humidity": float(humidity[i]) if humidity[i] is not None else None,
                "wind_speed": float(winds[i]) if winds[i] is not None else None,
                "is_forecast": is_forecast,
                "source": "open-meteo"
            })
            
        context.records_processed = len(results)
        return results

    def load(self, context, db, transformed_data, **kwargs):
        self.logger.info("Loading weather records to database...")
        
        inserted = 0
        updated = 0
        
        # Batch load existing weather record timestamps for open-meteo source to avoid redundant inserts
        timestamps = [r["timestamp"] for r in transformed_data]
        min_ts, max_ts = min(timestamps), max(timestamps)
        
        existing_weather = db.query(Weather).filter(
            Weather.source == "open-meteo",
            Weather.timestamp >= min_ts,
            Weather.timestamp <= max_ts
        ).all()
        
        existing_map = {w.timestamp: w for w in existing_weather}
        
        for w_dict in transformed_data:
            ts = w_dict["timestamp"]
            if ts in existing_map:
                # Update properties
                w_record = existing_map[ts]
                w_record.temperature = w_dict["temperature"]
                w_record.rainfall = w_dict["rainfall"]
                w_record.humidity = w_dict["humidity"]
                w_record.wind_speed = w_dict["wind_speed"]
                w_record.is_forecast = w_dict["is_forecast"]
                updated += 1
            else:
                # Insert new record
                w_record = Weather(
                    timestamp=ts,
                    temperature=w_dict["temperature"],
                    rainfall=w_dict["rainfall"],
                    humidity=w_dict["humidity"],
                    wind_speed=w_dict["wind_speed"],
                    is_forecast=w_dict["is_forecast"],
                    source="open-meteo"
                )
                db.add(w_record)
                inserted += 1
                
        db.commit()
        context.records_inserted = inserted
        context.records_updated = updated

    def verify(self, context, db, **kwargs):
        count = db.query(Weather).filter(Weather.source == "open-meteo").count()
        self.logger.info(f"Total weather records for source 'open-meteo' in database: {count}")
