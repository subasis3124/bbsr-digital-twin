import numpy as np
import pandas as pd
from typing import Tuple

class TemporalTrafficSplitter:
    """
    Splits traffic time-series features dataset chronologically.
    Ensures that validation data follows training, and test follows validation, globally.
    """
    
    @staticmethod
    def split(
        df: pd.DataFrame, 
        train_ratio: float = 0.7, 
        val_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Chronologically partitions the features dataframe.
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            
        # Ensuresorted order
        df_sorted = df.sort_values(by="timestamp").reset_index(drop=True)
        timestamps = df_sorted["timestamp"].unique()
        timestamps = np.sort(timestamps)
        
        n_times = len(timestamps)
        train_idx = int(n_times * train_ratio)
        val_idx = int(n_times * (train_ratio + val_ratio))
        
        # Determine strict threshold timestamps
        train_threshold = timestamps[train_idx]
        val_threshold = timestamps[val_idx]
        
        df_train = df[df["timestamp"] < train_threshold].copy()
        df_val = df[(df["timestamp"] >= train_threshold) & (df["timestamp"] < val_threshold)].copy()
        df_test = df[df["timestamp"] >= val_threshold].copy()
        
        # Chronological Split Integrity Assertions
        if not df_train.empty and not df_val.empty:
            assert df_train["timestamp"].max() < df_val["timestamp"].min(), \
                f"Leakage detected: Train max {df_train['timestamp'].max()} >= Val min {df_val['timestamp'].min()}"
                
        if not df_val.empty and not df_test.empty:
            assert df_val["timestamp"].max() < df_test["timestamp"].min(), \
                f"Leakage detected: Val max {df_val['timestamp'].max()} >= Test min {df_test['timestamp'].min()}"
                
        return df_train, df_val, df_test
