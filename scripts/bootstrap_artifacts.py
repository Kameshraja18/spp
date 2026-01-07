"""Generate placeholder model artifacts for development.

- Creates a baseline RandomForest model artifact at artifacts/rf_model.joblib
- Creates an untrained LSTM state_dict at artifacts/lstm_state_dict.pt

Use real training scripts for production models:
- python services/models/training/train_rf.py data/your_tabular.csv --output artifacts/rf_model.joblib
- python services/models/training/train_lstm.py data/your_sequences.csv --output artifacts/lstm_state_dict.pt
"""

import sys
from pathlib import Path

# Resolve services module when run from any directory
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

import joblib
import torch

from services.models.lstm_model import LSTMRiskModel
from services.models.rf_model import default_rf

ARTIFACTS_DIR = Path("artifacts")
RF_PATH = ARTIFACTS_DIR / "rf_model.joblib"
LSTM_PATH = ARTIFACTS_DIR / "lstm_state_dict.pt"


def make_rf_placeholder():
    model = default_rf()
    # Leave untrained placeholder; caller should replace with trained model.
    joblib.dump({"model": model, "feature_names": []}, RF_PATH)
    print(f"Wrote RF placeholder -> {RF_PATH}")


def make_lstm_placeholder():
    model = LSTMRiskModel()
    torch.save(model.state_dict(), LSTM_PATH)
    print(f"Wrote LSTM placeholder -> {LSTM_PATH}")


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    make_rf_placeholder()
    make_lstm_placeholder()


if __name__ == "__main__":
    main()
