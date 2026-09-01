import numpy as np
import pandas as pd
from typing import Tuple

class TemporalAirQualitySplitter:
    """
    Splits air quality time-series dataset chronologically.
    Ensures that validation data follows training, and test follows validation.
    Maintains strict max(train) < min(val) < min(test) partitioning.
    """

    @staticmethod
    def split(
        df: pd.DataFrame,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Chronologically partitions the features dataframe.
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df_sorted = df.sort_values(by="timestamp").reset_index(drop=True)
        timestamps = np.sort(df_sorted["timestamp"].unique())

        n_times = len(timestamps)
        if n_times < 3:
            return df_sorted.copy(), pd.DataFrame(), pd.DataFrame()

        train_idx = int(n_times * train_ratio)
        val_idx = int(n_times * (train_ratio + val_ratio))

        # Ensure index boundaries leave at least 1 timestamp for val and test
        train_idx = max(1, min(train_idx, n_times - 2))
        val_idx = max(train_idx + 1, min(val_idx, n_times - 1))

        train_threshold = timestamps[train_idx]
        val_threshold = timestamps[val_idx]

        df_train = df_sorted[df_sorted["timestamp"] < train_threshold].copy()
        df_val = df_sorted[(df_sorted["timestamp"] >= train_threshold) & (df_sorted["timestamp"] < val_threshold)].copy()
        df_test = df_sorted[df_sorted["timestamp"] >= val_threshold].copy()

        # Chronological Split Integrity Assertions
        if not df_train.empty and not df_val.empty:
            assert df_train["timestamp"].max() < df_val["timestamp"].min(), \
                f"Leakage detected: Train max {df_train['timestamp'].max()} >= Val min {df_val['timestamp'].min()}"

        if not df_val.empty and not df_test.empty:
            assert df_val["timestamp"].max() < df_test["timestamp"].min(), \
                f"Leakage detected: Val max {df_val['timestamp'].max()} >= Test min {df_test['timestamp'].min()}"

        return df_train, df_val, df_test
