import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, GCNConv, GATConv

class GraphSAGEPredictor(nn.Module):
    """
    GraphSAGE (Sample and Aggregate) model for node-level urban traffic forecasting.
    """
    def __init__(self, in_channels: int, hidden_channels: int, out_channels: int = 1, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.num_layers = num_layers
        self.dropout = dropout
        self.convs = nn.ModuleList()

        self.convs.append(SAGEConv(in_channels, hidden_channels, aggr="mean"))
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels, aggr="mean"))
        if num_layers > 1:
            self.convs.append(SAGEConv(hidden_channels, hidden_channels, aggr="mean"))

        self.head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        for conv in self.convs:
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        return self.head(x)


class GCNPredictor(nn.Module):
    """
    Graph Convolutional Network (GCN) model for node-level urban traffic forecasting.
    """
    def __init__(self, in_channels: int, hidden_channels: int, out_channels: int = 1, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.num_layers = num_layers
        self.dropout = dropout
        self.convs = nn.ModuleList()

        self.convs.append(GCNConv(in_channels, hidden_channels))
        for _ in range(num_layers - 2):
            self.convs.append(GCNConv(hidden_channels, hidden_channels))
        if num_layers > 1:
            self.convs.append(GCNConv(hidden_channels, hidden_channels))

        self.head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        for conv in self.convs:
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        return self.head(x)


class GATPredictor(nn.Module):
    """
    Graph Attention Network (GAT) model for node-level urban traffic forecasting.
    """
    def __init__(self, in_channels: int, hidden_channels: int, out_channels: int = 1, num_layers: int = 2, heads: int = 2, dropout: float = 0.1):
        super().__init__()
        self.num_layers = num_layers
        self.dropout = dropout
        self.convs = nn.ModuleList()

        self.convs.append(GATConv(in_channels, hidden_channels, heads=heads, concat=True))
        in_dim = hidden_channels * heads
        for _ in range(num_layers - 2):
            self.convs.append(GATConv(in_dim, hidden_channels, heads=heads, concat=True))
        if num_layers > 1:
            self.convs.append(GATConv(in_dim, hidden_channels, heads=1, concat=False))

        out_dim = hidden_channels
        self.head = nn.Sequential(
            nn.Linear(out_dim, out_dim // 2),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(out_dim // 2, out_channels)
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        for conv in self.convs:
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        return self.head(x)


class GNNTrafficForecaster(nn.Module):
    """
    Unified PyTorch GNN Wrapper supporting GraphSAGE, GCN, and GAT architectures.
    """
    def __init__(
        self,
        architecture: str = "GraphSAGE",
        in_channels: int = 14,
        hidden_channels: int = 64,
        out_channels: int = 1,
        num_layers: int = 2,
        dropout: float = 0.1
    ):
        super().__init__()
        self.architecture = architecture
        arch_upper = architecture.upper()

        if arch_upper in ["GRAPHSAGE", "SAGE"]:
            self.model = GraphSAGEPredictor(in_channels, hidden_channels, out_channels, num_layers, dropout)
        elif arch_upper == "GCN":
            self.model = GCNPredictor(in_channels, hidden_channels, out_channels, num_layers, dropout)
        elif arch_upper == "GAT":
            self.model = GATPredictor(in_channels, hidden_channels, out_channels, num_layers=num_layers, dropout=dropout)
        else:
            raise ValueError(f"Unsupported GNN architecture '{architecture}'. Choose GraphSAGE, GCN, or GAT.")

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        return self.model(x, edge_index)
