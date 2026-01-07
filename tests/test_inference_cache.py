import numpy as np
import pytest

from services.api.schemas import SeverityPredictionRequest
from services.models import inference


class DummyRF:
    def predict_proba(self, x):
        return np.array([[0.1, 0.2, 0.3, 0.4]])


@pytest.mark.asyncio
async def test_severity_uses_cached_risk(monkeypatch):
    captured = {}

    def fake_build(payload):
        captured["risk"] = payload.lstm_risk_score
        return np.zeros((1, 4), dtype=np.float32), ["f1", "f2", "f3", "f4"]

    monkeypatch.setattr(inference, "get_rf_model", lambda: DummyRF())
    monkeypatch.setattr(inference.cache, "get_latest_risk", lambda segment: 0.9)
    monkeypatch.setattr(inference.features, "build_severity_features", fake_build)

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

    resp = await inference.predict_severity(payload)

    assert captured.get("risk") == 0.9
    assert resp.severity_label == "fatal"
