import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
from typing import Dict, Any, Tuple

class NaiveForecaster:
    """
    Naive previous-value baseline.
    Predicts the future speed at t using the observed speed at t-1.
    """
    def __init__(self):
        pass
        
    def fit(self, X: pd.DataFrame, y: np.ndarray = None):
        return self
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X["lag_observed_speed_1h"].values

class HistoricalAverageForecaster:
    """
    Historical-average baseline.
    Predicts speed using the historical mean of speed for each road.
    """
    def __init__(self):
        self.road_means = {}
        self.global_mean = 40.0
        
    def fit(self, X: pd.DataFrame, y: np.ndarray):
        df = X.copy()
        df["target"] = y
        self.road_means = df.groupby("road_id")["target"].mean().to_dict()
        self.global_mean = float(np.mean(y))
        return self
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return X["road_id"].map(self.road_means).fillna(self.global_mean).values

def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculates standard regression evaluation metrics (MAE, RMSE, R2).
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2)
    }
