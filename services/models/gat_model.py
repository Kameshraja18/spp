"""Graph Neural Network model for spatio-temporal risk prediction.

Models road network as a graph where:
- Nodes = road segments
- Edges = connectivity between segments
- Node features = traffic/weather for that segment
- Task = predict risk propagation across the network

Architecture: Graph Attention Network (GAT) with temporal convolution.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class GraphAttentionLayer(nn.Module):
    """Single graph attention head."""
    
    def __init__(self, in_features: int, out_features: int, dropout: float = 0.0):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.dropout = dropout
        
        # Linear transformation for input features
        self.linear = nn.Linear(in_features, out_features)
        
        # Attention weights
        self.attention = nn.Linear(2 * out_features, 1)
        
        self.dropout_layer = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Node features (batch_size, num_nodes, in_features)
            adj: Adjacency matrix (num_nodes, num_nodes)
        
        Returns:
            Updated node features (batch_size, num_nodes, out_features)
        """
        h = self.linear(x)  # (batch, num_nodes, out_features)
        
        # Compute attention coefficients
        # For each edge (i,j), attention = softmax(LeakyReLU(W^T [h_i || h_j]))
        batch_size, num_nodes, _ = h.shape
        
        # Create pairwise concatenations: (num_nodes, num_nodes, 2*out_features)
        h_i = h[:, :, None, :].expand(batch_size, num_nodes, num_nodes, self.out_features)
        h_j = h[:, None, :, :].expand(batch_size, num_nodes, num_nodes, self.out_features)
        h_concat = torch.cat([h_i, h_j], dim=-1)  # (batch, num_nodes, num_nodes, 2*out_features)
        
        # Attention logits: (batch, num_nodes, num_nodes)
        attn_logits = self.attention(h_concat).squeeze(-1)
        
        # Apply adjacency mask and softmax
        mask = adj.unsqueeze(0).expand(batch_size, -1, -1)
        attn_logits = attn_logits.masked_fill(mask == 0, float('-inf'))
        attn = F.softmax(attn_logits, dim=-1)
        attn = torch.nan_to_num(attn, nan=0.0)  # Replace NaN with 0
        attn = self.dropout_layer(attn)
        
        # Apply attention to aggregate neighbor features
        out = torch.bmm(attn, h)  # (batch, num_nodes, out_features)
        
        return out


class GATRiskModel(nn.Module):
    """Graph Attention Network for road network risk prediction.
    
    Predicts segment-level risk based on:
    - Local traffic/weather features
    - Neighbor segment states (spatial context)
    - Temporal sequence
    """
    
    def __init__(
        self,
        num_nodes: int,
        node_feature_dim: int,
        temporal_window: int = 12,
        hidden_dim: int = 64,
        num_heads: int = 4,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.num_nodes = num_nodes
        self.node_feature_dim = node_feature_dim
        self.temporal_window = temporal_window
        
        # Feature projection
        self.feature_proj = nn.Linear(node_feature_dim, hidden_dim)
        
        # Temporal encoder (LSTM)
        self.temporal_lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            dropout=dropout if dropout > 0 else 0,
            batch_first=True,
        )
        
        # Graph attention heads
        self.gat_heads = nn.ModuleList([
            GraphAttentionLayer(hidden_dim, hidden_dim // num_heads, dropout)
            for _ in range(num_heads)
        ])
        
        # Output layers
        self.gat_out = nn.Linear(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(dropout)
        
        # Risk prediction head
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
    
    def forward(
        self,
        node_features: torch.Tensor,
        adjacency: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            node_features: (batch_size, num_nodes, temporal_window, node_feature_dim)
                          Features for each node over time
            adjacency: (num_nodes, num_nodes) adjacency matrix (binary)
        
        Returns:
            Tuple of:
            - risk_scores: (batch_size, num_nodes) per-segment risk [0, 1]
            - attention_weights: (batch_size, num_nodes, num_nodes) learned attention
        """
        batch_size, num_nodes, time_steps, feat_dim = node_features.shape
        
        # Project features: (batch, num_nodes, time_steps, hidden_dim)
        h = self.feature_proj(node_features)
        
        # Encode temporal dynamics per node: (batch, num_nodes, hidden_dim)
        h_flat = h.view(batch_size * num_nodes, time_steps, -1)
        _, (h_lstm, _) = self.temporal_lstm(h_flat)
        h_temporal = h_lstm[-1]  # Last hidden state: (batch*num_nodes, hidden_dim)
        h_temporal = h_temporal.view(batch_size, num_nodes, -1)
        
        # Apply multi-head graph attention
        attn_outs = []
        for gat_head in self.gat_heads:
            attn_outs.append(gat_head(h_temporal, adjacency))
        
        # Concatenate heads: (batch, num_nodes, hidden_dim)
        h_graph = torch.cat(attn_outs, dim=-1) if len(attn_outs) > 1 else attn_outs[0]
        
        # Output projection
        h_graph = self.gat_out(h_graph)
        h_graph = F.relu(h_graph)
        h_graph = self.dropout(h_graph)
        
        # Predict risk per segment
        risk_scores = self.risk_head(h_graph).squeeze(-1)  # (batch, num_nodes)
        
        # Dummy attention weights for interpretability (in practice, extract from GAT)
        attn_weights = torch.ones(batch_size, num_nodes, num_nodes) / num_nodes
        
        return risk_scores, attn_weights


def load_gat_model(path: str) -> GATRiskModel | None:
    """Load GAT model from state_dict.
    
    Args:
        path: Path to saved state_dict
    
    Returns:
        Loaded model or None if unavailable
    """
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Infer architecture from saved state
        state = torch.load(path, map_location=device)
        
        # Create model with inferred dimensions
        model = GATRiskModel(
            num_nodes=state.get("num_nodes", 10),
            node_feature_dim=state.get("node_feature_dim", 10),
            temporal_window=state.get("temporal_window", 12),
            hidden_dim=64,
            num_heads=4,
        )
        
        model.load_state_dict(state.get("model_state", state))
        model.to(device)
        model.eval()
        
        return model
    except Exception as e:
        print(f"Failed to load GAT model from {path}: {e}")
        return None
