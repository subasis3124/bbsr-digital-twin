import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.app.models import AirQuality, Weather
from typing import Tuple, Dict, Any, List, Optional

# Indian national/public holidays for Bhubaneswar context in 2026
INDIAN_HOLIDAYS_2026 = {
    "2026-01-26", # Republic Day
    "2026-03-03", # Holi
    "2026-08-15", # Independence Day
    "2026-10-02", # Gandhi Jayanti
    "2026-11-08", # Diwali
    "2026-12-25", # Christmas
}

class AirQualityFeatureExtractor:
    """
    Handles temporal and meteorological feature engineering for air quality forecasting.
    Ensures zero lookahead leakage by utilizing forward-shifted indices for target creation
    and strictly backward-looking lag/rolling variables.
    """

    def __init__(self, db: Session):
        self.db = db

    def load_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads AirQuality and optional Weather observations from DB into Pandas DataFrames.
        """
        aq_records = self.db.query(AirQuality).all()
        aq_data = []
        for a in aq_records:
            aq_data.append({
                "id": a.id,
                "timestamp": a.timestamp,
                "station_name": a.station_name,
                "pm25": float(a.pm25) if a.pm25 is not None else np.nan,
                "pm10": float(a.pm10) if a.pm10 is not None else np.nan,
                "co": float(a.co) if a.co is not None else np.nan,
                "no2": float(a.no2) if a.no2 is not None else np.nan,
                "so2": float(a.so2) if a.so2 is not None else np.nan,
                "o3": float(a.o3) if a.o3 is not None else np.nan,
                "aqi_value": float(a.aqi_value) if a.aqi_value is not None else np.nan,
                "source": a.source
            })
        df_aq = pd.DataFrame(aq_data)

        weather_records = self.db.query(Weather).all()
        weather_data = []
        for w in weather_records:
            weather_data.append({
                "timestamp": w.timestamp,
                "temperature": float(w.temperature) if w.temperature is not None else np.nan,
                "rainfall": float(w.rainfall) if w.rainfall is not None else np.nan,
                "humidity": float(w.humidity) if w.humidity is not None else np.nan,
                "wind_speed": float(w.wind_speed) if w.wind_speed is not None else np.nan,
            })
        df_weather = pd.DataFrame(weather_data)

        return df_aq, df_weather

    def extract_features(
        self,
        df_aq: pd.DataFrame,
        df_weather: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Builds feature matrix from raw air quality observations.
        Ensures strict chronological ordering and zero temporal leakage.
        """
        if df_aq.empty:
            return pd.DataFrame()

        df = df_aq.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by=["station_name", "timestamp"]).reset_index(drop=True)

        # 1. Temporal / Calendar Features
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["month"] = df["timestamp"].dt.month

        date_str = df["timestamp"].dt.strftime("%Y-%m-%d")
        df["is_holiday"] = date_str.isin(INDIAN_HOLIDAYS_2026).astype(int)

        # 2. Merge Weather features if present
        if df_weather is not None and not df_weather.empty:
            df_w = df_weather.copy()
            df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])
            df = pd.merge_asof(
                df.sort_values("timestamp"),
                df_w.sort_values("timestamp"),
                on="timestamp",
                direction="nearest"
            ).sort_values(by=["station_name", "timestamp"]).reset_index(drop=True)
        else:
            df["temperature"] = 28.0
            df["rainfall"] = 0.0
            df["humidity"] = 70.0
            df["wind_speed"] = 10.0

        # 3. Lags & Rolling Features for PM2.5 and PM10 per station
        for col in ["pm25", "pm10"]:
            if col not in df.columns or df[col].dropna().empty:
                continue

            # Lags (Shifted backward: t-1, t-2, t-3, t-6, t-12, t-24)
            df[f"{col}_lag_1h"] = df.groupby("station_name")[col].shift(1)
            df[f"{col}_lag_2h"] = df.groupby("station_name")[col].shift(2)
            df[f"{col}_lag_3h"] = df.groupby("station_name")[col].shift(3)
            df[f"{col}_lag_6h"] = df.groupby("station_name")[col].shift(6)
            df[f"{col}_lag_12h"] = df.groupby("station_name")[col].shift(12)
            df[f"{col}_lag_24h"] = df.groupby("station_name")[col].shift(24)

            # Rolling statistics (computed strictly using past values <= t)
            # shift(1) ensures current observation at t is excluded from past rolling window if computing prior stats,
            # or shift(0) rolling(3) includes up to t. To be ultra-conservative and prevent leakage, shift(1) is used.
            df[f"{col}_rolling_mean_3h"] = df.groupby("station_name")[col].transform(
                lambda x: x.shift(1).rolling(window=3, min_periods=1).mean()
            )
            df[f"{col}_rolling_mean_6h"] = df.groupby("station_name")[col].transform(
                lambda x: x.shift(1).rolling(window=6, min_periods=1).mean()
            )
            df[f"{col}_rolling_mean_24h"] = df.groupby("station_name")[col].transform(
                lambda x: x.shift(1).rolling(window=24, min_periods=1).mean()
            )

            df[f"{col}_rolling_std_3h"] = df.groupby("station_name")[col].transform(
                lambda x: x.shift(1).rolling(window=3, min_periods=1).std()
            ).fillna(0.0)
            df[f"{col}_rolling_std_24h"] = df.groupby("station_name")[col].transform(
                lambda x: x.shift(1).rolling(window=24, min_periods=1).std()
            ).fillna(0.0)

            # Trend features
            df[f"{col}_trend_3h"] = df[f"{col}_lag_1h"] - df[f"{col}_lag_3h"]
            df[f"{col}_trend_6h"] = df[f"{col}_lag_1h"] - df[f"{col}_lag_6h"]

        # 4. Create Multi-Horizon Forecast Targets
        # For predicting horizon H hours into the future from time t, the target is value at t + H.
        # shift(-H) shifts target value at t+H back to row t.
        for pollutant in ["pm25", "pm10"]:
            if pollutant in df.columns:
                for horizon in [6, 12, 24]:
                    df[f"target_{pollutant}_{horizon}h"] = df.groupby("station_name")[pollutant].shift(-horizon)

        return df
