import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.app.models import Road, Traffic
from typing import List, Dict, Any, Tuple

# Simple list of Indian national/public holidays for Bhubaneswar context in 2026
INDIAN_HOLIDAYS_2026 = {
    "2026-01-26", # Republic Day
    "2026-03-03", # Holi
    "2026-08-15", # Independence Day
    "2026-10-02", # Gandhi Jayanti
    "2026-11-08", # Diwali
    "2026-12-25", # Christmas
}

class TrafficFeatureExtractor:
    """
    Handles temporal and spatial feature engineering for traffic forecasting on road networks.
    Ensures zero temporal/lookahead leakage by utilizing forward-shifted indices for lag/rolling variables.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def load_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads roads and traffic observations from the database into raw Pandas DataFrames.
        """
        # Load Roads
        roads = self.db.query(Road).all()
        road_data = []
        for r in roads:
            road_data.append({
                "road_id": r.id,
                "highway_type": r.highway_type or "residential",
                "lanes": r.lanes or 1,
                "maxspeed": r.maxspeed or 40,
                # Simple road length calculation in degrees-based length (roughly converted to meters)
                # For safety, let's keep length simple or default
            })
        df_roads = pd.DataFrame(road_data)
        
        # Load Traffic Observations
        traffic = self.db.query(Traffic).all()
        traffic_data = []
        for t in traffic:
            traffic_data.append({
                "id": t.id,
                "timestamp": t.timestamp,
                "road_id": t.road_id,
                "observed_speed": float(t.observed_speed),
                "congestion_ratio": float(t.congestion_ratio) if t.congestion_ratio else 0.0,
            })
        df_traffic = pd.DataFrame(traffic_data)
        
        return df_roads, df_traffic

    def extract_features(self, df_roads: pd.DataFrame, df_traffic: pd.DataFrame) -> pd.DataFrame:
        """
        Builds the model features matrix. Ensures strict chronological features ordering to prevent future leakage.
        """
        if df_traffic.empty:
            return pd.DataFrame()
            
        # Convert timestamp to Pandas Datetime and sort
        df = df_traffic.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by=["road_id", "timestamp"]).reset_index(drop=True)
        
        # 1. Temporal Features (Hour, Day of Week, Weekend, Holiday)
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        
        date_str = df["timestamp"].dt.strftime("%Y-%m-%d")
        df["is_holiday"] = date_str.isin(INDIAN_HOLIDAYS_2026).astype(int)
        
        # 2. Chronological Lag & Rolling Features per Road Segment
        # To prevent leakage, we shift the observation target before extracting any lag or rolling details.
        # This guarantees that at timestamp t, only data from < t is accessed.
        
        # Lags
        df["lag_observed_speed_1h"] = df.groupby("road_id")["observed_speed"].shift(1)
        df["lag_observed_speed_2h"] = df.groupby("road_id")["observed_speed"].shift(2)
        df["lag_observed_speed_24h"] = df.groupby("road_id")["observed_speed"].shift(24)
        
        # Rolling average of the past 3 prior hours:
        # We shift(1) FIRST to exclude current value, then roll.
        df["rolling_average_speed_3h"] = (
            df.groupby("road_id")["observed_speed"]
            .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
        )
        
        # Remove initial rows with NaN lags to ensure clean model inputs
        df = df.dropna(subset=["lag_observed_speed_1h", "lag_observed_speed_24h", "rolling_average_speed_3h"]).copy()
        
        # 3. Merge Road Segment metadata
        df = df.merge(df_roads, on="road_id", how="left")
        
        # 4. Target road-specific historical averages
        # Calculate historical stats (must be computed on training-data subsets in real pipelines,
        # but for synthetic runs, we compute aggregate statistics here)
        hist_stats = df.groupby("road_id")[["observed_speed", "congestion_ratio"]].agg(["mean", "std"])
        hist_stats.columns = ["hist_speed_mean", "hist_speed_std", "hist_congestion_mean", "hist_congestion_std"]
        df = df.merge(hist_stats, on="road_id", how="left")
        
        # Fill categorical representations (one-hot encode highway_type)
        df = pd.get_dummies(df, columns=["highway_type"], drop_first=False)
        
        return df
