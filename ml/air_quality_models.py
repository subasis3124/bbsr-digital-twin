import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from typing import Dict, Any, Tuple, Optional

class NaiveAirQualityForecaster:
    """
    Naive baseline for air quality.
    Predicts the future pollutant concentration at T+H using the last observed concentration at T.
    """
    def __init__(self, pollutant: str = "pm25"):
        self.pollutant = pollutant

    def fit(self, X: pd.DataFrame, y: np.ndarray = None):
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        lag_col = f"{self.pollutant}_lag_1h"
        if lag_col in X.columns:
            return X[lag_col].fillna(0.0).values
        elif self.pollutant in X.columns:
            return X[self.pollutant].fillna(0.0).values
        return np.zeros(len(X))

class HistoricalAverageAirQualityForecaster:
    """
    Historical-average baseline.
    Predicts pollutant concentration using the historical mean per station.
    """
    def __init__(self, pollutant: str = "pm25"):
        self.pollutant = pollutant
        self.station_means: Dict[str, float] = {}
        self.global_mean: float = 35.0

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        df = X.copy()
        df["target"] = y
        if "station_name" in df.columns:
            self.station_means = df.groupby("station_name")["target"].mean().to_dict()
        valid_y = y[~np.isnan(y)]
        if len(valid_y) > 0:
            self.global_mean = float(np.mean(valid_y))
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "station_name" in X.columns:
            return X["station_name"].map(self.station_means).fillna(self.global_mean).values
        return np.full(len(X), self.global_mean)

def calculate_air_quality_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculates regression metrics (MAE, RMSE, R2) for air quality forecasting.
    Handles NaNs cleanly.
    """
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not np.any(mask):
        return {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0}

    y_t = y_true[mask]
    y_p = y_pred[mask]

    mae = mean_absolute_error(y_t, y_p)
    rmse = np.sqrt(mean_squared_error(y_t, y_p))

    # If y_true is constant or has 1 sample, r2_score can throw warning or return NaN
    if len(y_t) > 1 and np.var(y_t) > 1e-8:
        r2 = r2_score(y_t, y_p)
    else:
        r2 = 1.0 if np.allclose(y_t, y_p) else 0.0

    return {
        "MAE": float(round(mae, 4)),
        "RMSE": float(round(rmse, 4)),
        "R2": float(round(r2, 4))
    }
