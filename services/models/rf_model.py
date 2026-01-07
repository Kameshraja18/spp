from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


class RFSeverityModel:
    def __init__(self, model: RandomForestClassifier, feature_names: Optional[list[str]] = None):
        self.model = model
        self.feature_names = feature_names or []

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


def default_rf() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
    )


def load_rf(path: str | None) -> RFSeverityModel | None:
    if path is None:
        return None
    artifact = Path(path)
    if not artifact.exists():
        return None
    try:
        data = joblib.load(artifact)
        if isinstance(data, dict) and "model" in data:
            model = data["model"]
            feature_names = data.get("feature_names")
        else:
            model = data
            feature_names = None
        if not hasattr(model, "predict_proba"):
            return None
        return RFSeverityModel(model=model, feature_names=feature_names)
    except Exception:
        return None
