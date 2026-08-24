import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
import logging

logger = logging.getLogger("ML.SpatialCV")

class SpatialBlockSplitter:
    """
    Applies spatial block grouping and executes GroupKFold splits to prevent
    nearby grid cells from leaking correlations between train and test cycles.
    """
    def __init__(self, block_size_degrees: float = 0.02, n_splits: int = 5):
        self.block_size = block_size_degrees
        self.n_splits = n_splits

    def split(self, df: pd.DataFrame, x_col: str = "lon", y_col: str = "lat", label_col: str = "target"):
        """
        Creates spatial blocks based on coordinate ranges and generates splits page.
        Yields:
            train_idx, val_idx for each fold.
        """
        # Determine minimum bounding coordinates
        min_x = df[x_col].min()
        min_y = df[y_col].min()
        
        # Segment cells into spatial grid block integers
        block_x = np.floor((df[x_col] - min_x) / self.block_size).astype(int)
        block_y = np.floor((df[y_col] - min_y) / self.block_size).astype(int)
        
        # Unique block identifiers
        blocks = block_x * 1000 + block_y
        df["spatial_block_id"] = blocks
        
        unique_blocks_count = len(df["spatial_block_id"].unique())
        logger.info(f"Created {unique_blocks_count} spatial blocks for validation grouping (size={self.block_size} deg).")
        
        n_splits_adj = min(self.n_splits, unique_blocks_count)
        if n_splits_adj < self.n_splits:
            logger.warning(f"Requested splits {self.n_splits} is larger than available blocks {unique_blocks_count}. Adjusted to {n_splits_adj}.")
            
        gkf = GroupKFold(n_splits=n_splits_adj)
        
        X = df.drop(columns=[label_col]) if label_col in df.columns else df
        y = df[label_col] if label_col in df.columns else np.zeros(len(df))
        groups = df["spatial_block_id"]
        
        return gkf.split(X, y, groups=groups)
