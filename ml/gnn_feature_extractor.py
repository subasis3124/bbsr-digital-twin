import torch
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import Road, Traffic
from ml.graph_builder import UrbanGraphBuilder

INDIAN_HOLIDAYS_2026 = {
    "2026-01-26", "2026-03-03", "2026-08-15",
    "2026-10-02", "2026-11-08", "2026-12-25"
}

class GNNFeatureExtractor:
    """
    Extracts dynamic spatio-temporal node feature matrices for Graph Neural Networks.
    Guarantees strict zero temporal lookahead leakage.
    """

    def __init__(self, db: Session):
        self.db = db
        self.graph_builder = UrbanGraphBuilder(db)

    def extract_spatiotemporal_dataset(
        self,
        distance_threshold_meters: float = 0.0005
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extracts graph structure and timestamped node feature matrices.
        Returns graph dict and a list of time-step snapshot dictionaries:
        [{ "timestamp": dt, "X": Tensor[N, F], "y": Tensor[N, 1], "df_snapshot": DataFrame }]
        """
        # 1. Build spatial graph structure
        graph_data = self.graph_builder.build_graph(
            distance_threshold_meters=distance_threshold_meters,
            add_self_loops=True
        )

        num_nodes = graph_data["num_nodes"]
        road_to_idx = graph_data["road_to_idx"]
        idx_to_road = graph_data["idx_to_road"]
        x_static = graph_data["x_static"]

        if num_nodes == 0:
            return graph_data, []

        # 2. Query traffic observations
        traffic_obs = self.db.query(Traffic).all()
        if not traffic_obs:
            return graph_data, []

        traffic_records = []
        for t in traffic_obs:
            traffic_records.append({
                "road_id": t.road_id,
                "timestamp": t.timestamp,
                "observed_speed": float(t.observed_speed),
                "congestion_ratio": float(t.congestion_ratio) if t.congestion_ratio else 0.0
            })
        df_traffic = pd.DataFrame(traffic_records)
        df_traffic["timestamp"] = pd.to_datetime(df_traffic["timestamp"])
        df_traffic = df_traffic.sort_values(by=["road_id", "timestamp"]).reset_index(drop=True)

        # 3. Calculate chronological lags & rolling features per road segment (Zero Leakage)
        df_traffic["hour"] = df_traffic["timestamp"].dt.hour / 23.0
        df_traffic["day_of_week"] = df_traffic["timestamp"].dt.dayofweek / 6.0
        df_traffic["is_weekend"] = (df_traffic["timestamp"].dt.dayofweek >= 5).astype(float)
        date_str = df_traffic["timestamp"].dt.strftime("%Y-%m-%d")
        df_traffic["is_holiday"] = date_str.isin(INDIAN_HOLIDAYS_2026).astype(float)

        # Shift(1) FIRST before computing lags/rolling to exclude current target observation
        df_traffic["lag_observed_speed_1h"] = df_traffic.groupby("road_id")["observed_speed"].shift(1)
        df_traffic["lag_observed_speed_2h"] = df_traffic.groupby("road_id")["observed_speed"].shift(2)
        df_traffic["lag_observed_speed_24h"] = df_traffic.groupby("road_id")["observed_speed"].shift(24)

        df_traffic["rolling_average_speed_3h"] = (
            df_traffic.groupby("road_id")["observed_speed"]
            .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
        )

        # Drop incomplete initial lag rows
        df_clean = df_traffic.dropna(
            subset=["lag_observed_speed_1h", "lag_observed_speed_24h", "rolling_average_speed_3h"]
        ).copy()

        if df_clean.empty:
            return graph_data, []

        # 4. Group by timestamp to create spatial snapshots across all nodes
        timestamps = sorted(df_clean["timestamp"].unique())
        snapshots = []

        feature_cols = [
            "lag_observed_speed_1h",
            "lag_observed_speed_2h",
            "lag_observed_speed_24h",
            "rolling_average_speed_3h",
            "hour",
            "day_of_week",
            "is_weekend",
            "is_holiday"
        ]

        for ts in timestamps:
            df_ts = df_clean[df_clean["timestamp"] == ts]
            
            # Map road_id observations to node indices
            node_dyn_features = np.zeros((num_nodes, len(feature_cols)), dtype=np.float32)
            node_targets = np.zeros((num_nodes, 1), dtype=np.float32)
            mask = np.zeros((num_nodes,), dtype=bool)

            for _, row in df_ts.iterrows():
                rid = int(row["road_id"])
                if rid in road_to_idx:
                    node_idx = road_to_idx[rid]
                    node_dyn_features[node_idx] = row[feature_cols].values
                    node_targets[node_idx] = row["observed_speed"]
                    mask[node_idx] = True

            # Concatenate static node features and dynamic temporal features
            x_dyn = torch.tensor(node_dyn_features, dtype=torch.float32)
            y_target = torch.tensor(node_targets, dtype=torch.float32)
            x_combined = torch.cat([x_static, x_dyn], dim=1) # Shape [N, F_static + F_dyn]

            snapshots.append({
                "timestamp": ts,
                "X": x_combined,
                "y": y_target,
                "mask": torch.tensor(mask, dtype=torch.bool),
                "df_snapshot": df_ts
            })

        return graph_data, snapshots


class SpatiotemporalSplitter:
    """
    Chronologically partitions spatiotemporal graph snapshots into train, validation, and test sets.
    """

    @staticmethod
    def split(
        snapshots: List[Dict[str, Any]],
        train_ratio: float = 0.60,
        val_ratio: float = 0.20
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Splits snapshots chronologically.
        """
        if not snapshots:
            return [], [], []

        n = len(snapshots)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_snapshots = snapshots[:train_end]
        val_snapshots = snapshots[train_end:val_end]
        test_snapshots = snapshots[val_end:]

        return train_snapshots, val_snapshots, test_snapshots
