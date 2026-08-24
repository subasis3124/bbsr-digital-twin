import os
import requests
from datetime import datetime, timezone
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from pipelines.etl.base import BaseETLPipeline
from pipelines.etl.config import REQUEST_TIMEOUT
from backend.app.models import AirQuality

class AirQualityPipeline(BaseETLPipeline):
    def __init__(self):
        super().__init__("air_quality", "openaq-cpcb")
        self.latitude = 20.296
        self.longitude = 85.824
        self.station_name = "Bhubaneswar Central"
        self.api_key = os.getenv("OPENAQ_API_KEY", None)

    def discover(self, context, db, **kwargs):
        if self.api_key:
            self.logger.info("OpenAQ API Key detected. Testing v3 locations endpoint...")
            headers = {"X-API-Key": self.api_key}
            res = requests.get("https://api.openaq.org/v3/locations", headers=headers, timeout=REQUEST_TIMEOUT)
            self.logger.info(f"OpenAQ v3 locations response: {res.status_code}")
        else:
            self.logger.info("No OpenAQ API Key detected. Performing discovery on public Open-Meteo Air Quality endpoint...")
            url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "hourly": "pm2_5",
                "forecast_days": 1
            }
            res = requests.head(url, params=params, timeout=REQUEST_TIMEOUT)
            if res.status_code != 200:
                raise ConnectionError(f"Open-Meteo Air Quality check failed with status: {res.status_code}")

    def download(self, context, db, **kwargs):
        pass

    def validate(self, context, db, **kwargs) -> bool:
        return True

    def _calculate_aqi_pm25(self, pm25_val):
        """
        Calculate EPA standard AQI sub-index for PM2.5.
        """
        if pm25_val is None or pm25_val < 0:
            return None
            
        # EPA PM2.5 breakpoints
        breakpoints = [
            (0.0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500)
        ]
        
        for bp in breakpoints:
            clo, chi, ilo, ihi = bp
            if clo <= pm25_val <= chi:
                aqi = ((ihi - ilo) / (chi - clo)) * (pm25_val - clo) + ilo
                return int(round(aqi))
                
        if pm25_val > 500.4:
            return 500
        return 0

    def transform(self, context, db, **kwargs):
        if self.api_key:
            # Query OpenAQ using v3 structure
            return self._transform_openaq(context)
        else:
            # Query Open-Meteo Air Quality
            return self._transform_open_meteo_aq(context)

    def _transform_openaq(self, context):
        self.logger.info("Downloading from OpenAQ API v3...")
        # Since this runs in a headless environment, we implement
        # a standard query structure that falls back to Open-Meteo if OpenAQ returns errors.
        try:
            headers = {"X-API-Key": self.api_key}
            # Step 1: Find closest location in radius 25km
            loc_url = "https://api.openaq.org/v3/locations"
            params = {
                "coordinates": f"{self.latitude},{self.longitude}",
                "radius": 25000,
                "limit": 1
            }
            res = requests.get(loc_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
            loc_data = res.json()
            
            results = loc_data.get("results", [])
            if not results:
                self.logger.warning("No OpenAQ v3 locations found. Falling back to Open-Meteo AQ.")
                return self._transform_open_meteo_aq(context)
                
            loc = results[0]
            loc_name = loc.get("name", self.station_name)
            sensors = loc.get("sensors", [])
            
            # Map parameters by sensor IDs
            sensor_map = {}
            for s in sensors:
                parameter = s.get("parameter", {}).get("name", "")
                sensor_id = s.get("id")
                if parameter and sensor_id:
                    sensor_map[parameter] = sensor_id
                    
            if not sensor_map:
                return self._transform_open_meteo_aq(context)
                
            # Query measurements for PM2.5, PM10
            pm25_sensor = sensor_map.get("pm25")
            if not pm25_sensor:
                return self._transform_open_meteo_aq(context)
                
            meas_url = f"https://api.openaq.org/v3/sensors/{pm25_sensor}/measurements"
            meas_res = requests.get(meas_url, headers=headers, params={"limit": 48}, timeout=REQUEST_TIMEOUT)
            meas_res.raise_for_status()
            meas_data = meas_res.json()
            
            transformed = []
            for m in meas_data.get("results", []):
                # ISO datetime parses
                period = m.get("period", {})
                datetime_str = period.get("datetimeTo", {}).get("utc")
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                value = m.get("value")
                
                transformed.append({
                    "timestamp": dt,
                    "station_name": loc_name,
                    "pm25": float(value) if value is not None else None,
                    "pm10": None,
                    "co": None,
                    "no2": None,
                    "so2": None,
                    "o3": None,
                    "aqi_value": self._calculate_aqi_pm25(value),
                    "source": "openaq"
                })
            
            context.records_processed = len(transformed)
            return transformed
            
        except Exception as e:
            self.logger.warning(f"Error querying OpenAQ: {e}. Falling back to Open-Meteo Air Quality API.")
            return self._transform_open_meteo_aq(context)

    def _transform_open_meteo_aq(self, context):
        self.logger.info("Fetching Air Quality forecast from Open-Meteo Air Quality API...")
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "past_days": 3
        }
        
        res = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        pm2_5 = hourly.get("pm2_5", [])
        pm10 = hourly.get("pm10", [])
        co = hourly.get("carbon_monoxide", [])
        no2 = hourly.get("nitrogen_dioxide", [])
        so2 = hourly.get("sulphur_dioxide", [])
        o3 = hourly.get("ozone", [])
        
        transformed = []
        for i in range(len(times)):
            dt = datetime.fromisoformat(times[i]).replace(tzinfo=timezone.utc)
            pm25_val = float(pm2_5[i]) if pm2_5[i] is not None else None
            
            transformed.append({
                "timestamp": dt,
                "station_name": self.station_name,
                "pm25": pm25_val,
                "pm10": float(pm10[i]) if pm10[i] is not None else None,
                "co": float(co[i]) if co[i] is not None else None,
                "no2": float(no2[i]) if no2[i] is not None else None,
                "so2": float(so2[i]) if so2[i] is not None else None,
                "o3": float(o3[i]) if o3[i] is not None else None,
                "aqi_value": self._calculate_aqi_pm25(pm25_val),
                "source": "open-meteo-aq"
            })
            
        context.records_processed = len(transformed)
        return transformed

    def load(self, context, db, transformed_data, **kwargs):
        self.logger.info("Loading air quality logs to database with application-level upserts...")
        
        inserted = 0
        updated = 0
        
        timestamps = [r["timestamp"] for r in transformed_data]
        min_ts, max_ts = min(timestamps), max(timestamps)
        
        # Batch load existing rows to avoid duplicate checks
        existing_aq = db.query(AirQuality).filter(
            AirQuality.station_name == self.station_name,
            AirQuality.timestamp >= min_ts,
            AirQuality.timestamp <= max_ts
        ).all()
        
        existing_map = {a.timestamp: a for a in existing_aq}
        station_geom = from_shape(Point(self.longitude, self.latitude), srid=4326)
        
        for aq_dict in transformed_data:
            ts = aq_dict["timestamp"]
            if ts in existing_map:
                # Update
                aq_record = existing_map[ts]
                aq_record.pm25 = aq_dict["pm25"]
                aq_record.pm10 = aq_dict["pm10"]
                aq_record.co = aq_dict["co"]
                aq_record.no2 = aq_dict["no2"]
                aq_record.so2 = aq_dict["so2"]
                aq_record.o3 = aq_dict["o3"]
                aq_record.aqi_value = aq_dict["aqi_value"]
                updated += 1
            else:
                # Insert
                aq_record = AirQuality(
                    timestamp=ts,
                    station_name=aq_dict["station_name"],
                    pm25=aq_dict["pm25"],
                    pm10=aq_dict["pm10"],
                    co=aq_dict["co"],
                    no2=aq_dict["no2"],
                    so2=aq_dict["so2"],
                    o3=aq_dict["o3"],
                    aqi_value=aq_dict["aqi_value"],
                    geom=station_geom,
                    source=aq_dict["source"]
                )
                db.add(aq_record)
                inserted += 1
                
        db.commit()
        context.records_inserted = inserted
        context.records_updated = updated

    def verify(self, context, db, **kwargs):
        count = db.query(AirQuality).filter(AirQuality.station_name == self.station_name).count()
        self.logger.info(f"Verified {count} air quality stations records in database.")
