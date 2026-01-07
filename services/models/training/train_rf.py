"""Training script stub for RandomForest severity model.

- Expects a CSV with tabular features matching SeverityPredictionRequest fields.
- Applies simple preprocessing, class weights, and optional SMOTE on the training fold only.
- Saves a joblib artifact containing model and feature_names for inference.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so 'services' imports work regardless of cwd.
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import argparse
from typing import List

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from services.models.rf_model import default_rf

TARGET = "severity"


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, List[str]]:
    df = df.copy()
    # Basic preprocessing: fill missing numeric with 0, categorical with "unknown".
    cat_cols = [
        "weather",
        "weather_condition",  # NEW
        "light_condition",
        "road_type",
        "surface_condition",
    ]
    num_cols = [
        "avg_speed_current",
        "congestion_index_current",
        "historical_accident_rate_segment",
        "lstm_risk_score",
        # NEW: Enhanced weather features
        "temperature",
        "wind_speed",
        "visibility",
        "humidity",  # NEW
        "precipitation",  # NEW
        "cloud_cover",  # NEW
        "weather_risk_factor",
        # NEW: Enhanced rolling statistics (11 new features)
        "speed_variance",  # NEW
        "speed_range",  # NEW
        "speed_percentile_25",  # NEW
        "speed_percentile_75",  # NEW
        "speed_median",  # NEW
        "congestion_variance",  # NEW
        "congestion_range",  # NEW
        "congestion_median",  # NEW
        "flow_variance",  # NEW
        "flow_range",  # NEW
        "flow_median",  # NEW
    ]
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].fillna("unknown")
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].fillna(0)

    # One-hot encode categorical columns.
    existing_cat_cols = [c for c in cat_cols if c in df.columns]
    df_encoded = pd.get_dummies(df[existing_cat_cols], prefix=existing_cat_cols)
    
    # Select only existing numeric columns
    existing_num_cols = [c for c in num_cols if c in df.columns]
    feature_df = pd.concat([df_encoded, df[existing_num_cols]], axis=1)
    feature_names = list(feature_df.columns)
    x = feature_df.to_numpy(dtype=np.float32)
    return x, feature_names


def train(data_path: Path, output_path: Path, test_size: float = 0.2, smote: bool = True) -> None:
    df = pd.read_csv(data_path)
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' missing in data")

    y = df[TARGET].astype(int).to_numpy()
    x, feature_names = build_features(df)

    x_train, x_val, y_train, y_val = train_test_split(x, y, test_size=test_size, stratify=y, random_state=42)

    if smote:
        sm = SMOTE(random_state=42)
        x_train, y_train = sm.fit_resample(x_train, y_train)

    model = default_rf()
    model.fit(x_train, y_train)

    y_pred = model.predict(x_val)
    report = classification_report(y_val, y_pred, digits=3)
    print("Validation classification report:\n", report)

    artifact = {"model": model, "feature_names": feature_names}
    joblib.dump(artifact, output_path)
    print(f"Saved RF model to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path, help="Path to CSV containing training data")
    parser.add_argument("--output", type=Path, default=Path("artifacts/rf_model.joblib"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--no-smote", action="store_true", help="Disable SMOTE balancing")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    train(args.data, args.output, test_size=args.test_size, smote=not args.no_smote)
