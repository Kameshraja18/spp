from __future__ import annotations

try:
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore
    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover - environment-specific optional dependency
    torch = None
    nn = None
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
    class LSTMRiskModel(nn.Module):
        def __init__(self, input_dim: int = 7, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.3):
            super().__init__()
            self.lstm = nn.LSTM(
                input_dim,
                hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )

        def forward(self, x):  # x: (B, T, F)
            _, (h_n, _) = self.lstm(x)
            last_hidden = h_n[-1]
            return self.head(last_hidden)

        def predict_score(self, x):
            self.eval()
            with torch.no_grad():
                return self.forward(x).squeeze().item()
else:
    class LSTMRiskModel:
        def predict_score(self, x):
            return 0.5


def load_lstm(path: str | None) -> LSTMRiskModel | None:
    if not TORCH_AVAILABLE:
        return None
    model = LSTMRiskModel()
    if path:
        try:
            state = torch.load(path, map_location=torch.device("cpu"))
            model.load_state_dict(state)
        except FileNotFoundError:
            return None
        except Exception:
            return None
    return model
