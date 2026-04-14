import numpy as np
import torch

from services.api.schemas import RiskSequencePoint, SeverityPredictionRequest
from services.models import features


def test_sequence_to_tensor_shape():
    seq = [
        RiskSequencePoint(
            timestamp=np.datetime64("2024-01-01T01:00"),
            avg_speed=10,
            flow=1,
            occupancy=0.1,
            congestion_index=0.2,
            rain_intensity=0.0,
        )
        for _ in range(12)
    ]
    tensor = features.sequence_to_tensor(seq)
    assert tensor.shape == (1, 12, 7)
    assert isinstance(tensor, torch.Tensor)


def test_build_severity_features_defaults():
    payload = SeverityPredictionRequest(
        road_segment_id="S1",
        timestamp=np.datetime64("2024-01-01T00:00"),
        weather="Rain",
        light_condition="Dark",
        road_type="Highway",
        surface_condition="Wet",
        avg_speed_current=80.0,
        congestion_index_current=0.4,
        lstm_risk_score=None,
        historical_accident_rate_segment=None,
    )
    x, names = features.build_severity_features(payload)
    assert x.shape[0] == 1
    assert len(names) == x.shape[1]
    assert x.shape[1] >= 4  # numerical columns at minimum
