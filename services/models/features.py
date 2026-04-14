from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel

from services.api.schemas import RiskSequencePoint, SeverityPredictionRequest


CATEGORICAL_MAPS = {
    "weather": {},
    "light_condition": {},
    "road_type": {},
    "surface_condition": {},
}


def _one_hot(value: str, namespace: str) -> List[float]:
    mapping = CATEGORICAL_MAPS[namespace]
    if value not in mapping:
        mapping[value] = len(mapping)
    size = len(mapping)
    vec = [0.0] * size
    vec[mapping[value]] = 1.0
    return vec


def sequence_to_tensor(sequence: Sequence[RiskSequencePoint]) -> torch.Tensor:
    if not sequence:
        raise ValueError("recent_sequence is required for risk prediction")
    rows: List[List[float]] = []
    for point in sequence:
        rows.append(
            [
                point.avg_speed,
                point.flow,
                point.occupancy,
                point.congestion_index,
                point.rain_intensity,
                np.sin(point.timestamp.hour / 24 * 2 * np.pi),
                np.cos(point.timestamp.hour / 24 * 2 * np.pi),
            ]
        )
    arr = np.array(rows, dtype=np.float32)
    return torch.from_numpy(arr).unsqueeze(0)  # shape: (1, T, 7)


def build_severity_features(payload: SeverityPredictionRequest) -> Tuple[np.ndarray, List[str]]:
    cats = []
    cats += _one_hot(payload.weather, "weather")
    cats += _one_hot(payload.light_condition, "light_condition")
    cats += _one_hot(payload.road_type, "road_type")
    cats += _one_hot(payload.surface_condition, "surface_condition")

    numerics = [
        payload.avg_speed_current,
        payload.congestion_index_current,
        payload.historical_accident_rate_segment or 0.0,
        payload.lstm_risk_score or 0.5,
    ]

    feature_names = (
        [f"weather_{k}" for k in CATEGORICAL_MAPS["weather"]]
        + [f"light_{k}" for k in CATEGORICAL_MAPS["light_condition"]]
        + [f"road_{k}" for k in CATEGORICAL_MAPS["road_type"]]
        + [f"surface_{k}" for k in CATEGORICAL_MAPS["surface_condition"]]
        + [
            "avg_speed_current",
            "congestion_index_current",
            "historical_accident_rate_segment",
            "lstm_risk_score",
        ]
    )

    arr = np.array([cats + numerics], dtype=np.float32)
    return arr, feature_names


def build_explain_features(instance: Dict) -> Tuple[np.ndarray, List[str]]:
    df = pd.DataFrame([instance])
    df = df.fillna(0)
    feature_names = list(df.columns)
    arr = df.to_numpy(dtype=np.float32)
    return arr, feature_names


def counterfactual_hints(scored: List[Tuple[str, float]]):
    top = [name for name, _ in scored[:3]]
    hints = []
    for name in top:
        if "speed" in name:
            hints.append("Reduce speed limits or calm traffic on flagged segments.")
        elif "light" in name:
            hints.append("Improve lighting conditions during dark hours.")
        elif "weather" in name:
            hints.append("Add weather-aware signage and adjust limits when adverse conditions hit.")
    if not hints:
        hints.append("Review top features and apply targeted mitigations per segment.")
    return hints
