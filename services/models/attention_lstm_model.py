"""Attention-based LSTM for temporal risk prediction.

Combines LSTM with multi-head attention to learn which timesteps
and features are most important for risk prediction.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiHeadAttention(nn.Module):
    """Multi-head self-attention for sequence."""
    
    def __init__(self, hidden_dim: int, num_heads: int = 4, dropout: float = 0.0):
        super().__init__()
        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"
        
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        self.query = nn.Linear(hidden_dim, hidden_dim)
        self.key = nn.Linear(hidden_dim, hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)
        
        self.fc_out = nn.Linear(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor) -> torch.Tensor:
        """
        Args:
            query: (batch, seq_len, hidden_dim)
            key: (batch, seq_len, hidden_dim)
            value: (batch, seq_len, hidden_dim)
        
        Returns:
            (batch, seq_len, hidden_dim)
        """
        batch_size = query.shape[0]
        
        # Linear projections
        Q = self.query(query)  # (batch, seq_len, hidden_dim)
        K = self.key(key)
        V = self.value(value)
        
        # Reshape for multi-head: (batch, num_heads, seq_len, head_dim)
        Q = Q.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Scaled dot-product attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim ** 0.5)
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        out = torch.matmul(attn_weights, V)  # (batch, num_heads, seq_len, head_dim)
        out = out.transpose(1, 2).contiguous()  # (batch, seq_len, num_heads, head_dim)
        out = out.view(batch_size, -1, self.hidden_dim)
        
        out = self.fc_out(out)
        
        return out


class AttentionLSTMRiskModel(nn.Module):
    """LSTM with attention mechanism for temporal risk prediction.
    
    Architecture:
    1. LSTM encoder: learns temporal patterns
    2. Multi-head attention: learns which timesteps matter
    3. Risk head: predicts binary risk
    """
    
    def __init__(
        self,
        input_dim: int = 7,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_heads: int = 4,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM encoder
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True,  # Bidirectional context
        )
        
        # Attention over LSTM outputs
        self.attention = MultiHeadAttention(
            hidden_dim * 2,  # Bidirectional = 2x hidden_dim
            num_heads=num_heads,
            dropout=dropout,
        )
        
        # Fusion layer after attention
        self.fusion = nn.Linear(hidden_dim * 2, hidden_dim)
        
        # Risk prediction head
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        
        self.dropout_layer = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, input_dim) sequence of traffic features
        
        Returns:
            risk_score: (batch_size,) in [0, 1]
        """
        # LSTM forward: get outputs for all timesteps
        lstm_out, (h_n, c_n) = self.lstm(x)  # (batch, seq_len, hidden_dim*2)
        
        # Apply attention to learn important timesteps
        attn_out = self.attention(lstm_out, lstm_out, lstm_out)  # (batch, seq_len, hidden_dim*2)
        
        # Global average pooling over time dimension
        context = torch.mean(attn_out, dim=1)  # (batch, hidden_dim*2)
        
        # Fusion
        context = self.fusion(context)
        context = F.relu(context)
        context = self.dropout_layer(context)
        
        # Predict risk
        risk_score = self.risk_head(context).squeeze(-1)  # (batch,)
        
        return risk_score


def load_attention_lstm_model(path: str) -> AttentionLSTMRiskModel | None:
    """Load attention-LSTM model from state_dict.
    
    Args:
        path: Path to saved state_dict
    
    Returns:
        Loaded model or None if unavailable
    """
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        state = torch.load(path, map_location=device)
        
        # Create model with standard dimensions
        model = AttentionLSTMRiskModel(
            input_dim=7,
            hidden_dim=128,
            num_layers=2,
            num_heads=4,
            dropout=0.3,
        )
        
        model.load_state_dict(state)
        model.to(device)
        model.eval()
        
        return model
    except Exception as e:
        print(f"Failed to load attention-LSTM model from {path}: {e}")
        return None
