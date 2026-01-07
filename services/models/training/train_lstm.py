"""Training script stub for LSTM risk model.

- Expects a CSV with sequential samples pre-windowed: columns ['road_segment_id', 'timestamp', feature... , 'label']
- Groups by road_segment_id and sorts by timestamp, then builds sequences of length input_window.
- Saves a Torch state_dict suitable for inference via LSTMRiskModel.predict_score.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so 'services' imports work regardless of cwd.
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import argparse
from typing import List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from services.models.lstm_model import LSTMRiskModel

FEATURE_COLUMNS = [
    "avg_speed",
    "flow",
    "occupancy",
    "congestion_index",
    "rain_intensity",
    "time_of_day_sin",
    "time_of_day_cos",
    # NEW: Enhanced weather features (4 new)
    "humidity",
    "precipitation",
    "cloud_cover",
    "weather_risk_factor",
    # NEW: Enhanced rolling statistics (11 new features)
    "speed_variance",
    "speed_range",
    "speed_percentile_25",
    "speed_percentile_75",
    "speed_median",
    "congestion_variance",
    "congestion_range",
    "congestion_median",
    "flow_variance",
    "flow_range",
    "flow_median",
]


class SequenceDataset(Dataset):
    def __init__(self, df: pd.DataFrame, input_window: int):
        self.samples: List[Tuple[np.ndarray, float]] = []
        # Use only columns that exist in the dataframe
        available_features = [col for col in FEATURE_COLUMNS if col in df.columns]
        if len(available_features) < 5:
            raise ValueError(f"Too few features available. Found: {available_features}")
        
        for _, seg_df in df.groupby("road_segment_id"):
            seg_df = seg_df.sort_values("timestamp")
            values = seg_df[available_features].to_numpy(dtype=np.float32)
            labels = seg_df["label"].to_numpy(dtype=np.float32)
            for i in range(len(seg_df) - input_window):
                window = values[i : i + input_window]
                y = labels[i + input_window]
                self.samples.append((window, y))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        x, y = self.samples[idx]
        return torch.from_numpy(x), torch.tensor(y, dtype=torch.float32)


def make_time_encodings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    hours = pd.to_datetime(df["timestamp"]).dt.hour
    df["time_of_day_sin"] = np.sin(hours / 24 * 2 * np.pi)
    df["time_of_day_cos"] = np.cos(hours / 24 * 2 * np.pi)
    return df


def train(data_path: Path, output_path: Path, input_window: int = 12, epochs: int = 5, batch_size: int = 64, lr: float = 1e-3):
    df = pd.read_csv(data_path)
    df = make_time_encodings(df)
    dataset = SequenceDataset(df, input_window=input_window)
    if len(dataset) == 0:
        raise ValueError("No sequences constructed; check data shape and input_window")

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMRiskModel(input_dim=len(FEATURE_COLUMNS)).to(device)
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in tqdm(loader, desc=f"epoch {epoch+1}/{epochs}"):
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            preds = model(xb).squeeze()
            loss = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * xb.size(0)
        epoch_loss = total_loss / len(dataset)
        print(f"Epoch {epoch+1}: loss={epoch_loss:.4f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    print(f"Saved LSTM state_dict to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path, help="Path to CSV with sequential samples")
    parser.add_argument("--output", type=Path, default=Path("artifacts/lstm_state_dict.pt"))
    parser.add_argument("--input-window", type=int, default=12)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(
        data_path=args.data,
        output_path=args.output,
        input_window=args.input_window,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
