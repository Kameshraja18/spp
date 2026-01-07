"""Feature builder: transform raw traffic/weather into enriched model-ready payloads.

Enhanced behavior:
- Maintains a per-segment sliding window (maxlen=12) of sequence points.
- Normalizes inbound records into RiskPredictionRequest schema.
- Enriches with weather data, rolling statistics, and temporal features.
- Forwards enriched payloads to FEATURES_TOPIC.
- ENHANCED with Prometheus metrics and structured logging.
"""

from __future__ import annotations

from typing import Any, Dict

from collections import defaultdict, deque
import threading
import logging

from kafka import KafkaProducer

from services.api.schemas import RiskSequencePoint
from services.stream import config
from services.stream.pipeline import _make_producer
from services.models.weather_service import enrich_features_with_weather, compute_weather_risk_factor, get_weather
from services.models.rolling_stats import RollingStats
from services.models.temporal_features import extract_temporal_features, get_seasonal_risk_factor
from services.monitoring.metrics import (
    record_feature_enrichment,
    track_feature_enrichment,
    update_feature_value,
)

# Configure structured logging
logger = logging.getLogger(__name__)

WINDOW_SIZE = 12
_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
_rolling_stats: dict[str, RollingStats] = defaultdict(lambda: RollingStats(window_size=WINDOW_SIZE))
_lock = threading.Lock()


def _normalize_message(msg: Dict[str, Any]) -> Dict[str, Any]:
  """Ensure message aligns to RiskPredictionRequest schema (recent_sequence list)."""
  if "recent_sequence" in msg:
    return msg

  # Fallback: convert single traffic record into a 1-step sequence.
  point = RiskSequencePoint(
    timestamp=msg.get("timestamp"),
    avg_speed=float(msg.get("avg_speed", msg.get("speed", 0) or 0)),
    flow=float(msg.get("flow", 0) or 0),
    occupancy=float(msg.get("occupancy", 0) or 0),
    congestion_index=float(msg.get("congestion_index", 0) or 0),
    rain_intensity=float(msg.get("rain_intensity", msg.get("rain", 0) or 0)),
  )
  return {
    "road_segment_id": msg.get("road_segment_id", "unknown"),
    "recent_sequence": [point.model_dump()],
  }


def _update_window(segment_id: str, normalized: Dict[str, Any]) -> Dict[str, Any]:
  seq = normalized.get("recent_sequence") or []
  if not seq:
    return normalized
  with _lock:
    window = _windows[segment_id]
    for item in seq:
      window.append(item)
    normalized["recent_sequence"] = list(window)
  return normalized


@track_feature_enrichment("complete")
def build_features(msg: Dict[str, Any]) -> Dict[str, Any]:
  normalized = _normalize_message(msg)
  segment_id = normalized.get("road_segment_id", "unknown")
  normalized = _update_window(segment_id, normalized)
  
  seq = normalized.get("recent_sequence", [])
  if seq:
    # Extract latest timestamp for enrichment
    latest_item = seq[-1]
    timestamp = latest_item.get("timestamp", "")
    
    # Advanced rolling statistics
    rolling_stats_obj = _rolling_stats[segment_id]
    rolling_stats_obj.update(
      speed=latest_item.get("avg_speed", 0),
      congestion=latest_item.get("congestion_index", 0),
      flow=latest_item.get("flow", 0),
    )
    stats = rolling_stats_obj.get_stats()
    record_feature_enrichment("rolling_stats")
    
    # Temporal features
    temporal = extract_temporal_features(timestamp) if timestamp else {}
    record_feature_enrichment("temporal")
    
    # Weather enrichment
    weather = get_weather(segment_id, timestamp) if timestamp else {}
    weather_risk = compute_weather_risk_factor(weather)
    seasonal_risk = get_seasonal_risk_factor(timestamp) if timestamp else 1.0
    record_feature_enrichment("weather")
    
    # Combine all enrichments (ENHANCED with new weather fields)
    normalized.update({
      **stats,  # Rolling stats (speed_mean, congestion_std, etc.)
      **temporal,  # Temporal features (hour, day_of_week, hour_sin, etc.)
      "temperature": weather.get("temp", 15.0),
      "wind_speed": weather.get("wind_speed", 5.0),
      "visibility": weather.get("visibility", 10000.0),
      "humidity": weather.get("humidity", 60.0),
      "precipitation": weather.get("precipitation", 0.0),
      "cloud_cover": weather.get("cloud_cover", 50),
      "weather_condition": weather.get("condition", "clear"),
      "weather_risk_factor": weather_risk,
      "seasonal_risk_factor": seasonal_risk,
      "sequence_length": len(seq),
    })
    
    # Track key feature values for monitoring
    update_feature_value("weather_risk_factor", segment_id, weather_risk)
    update_feature_value("speed_mean", segment_id, stats.get("speed_mean", 0))
    update_feature_value("congestion_mean", segment_id, stats.get("congestion_mean", 0))
    
    logger.debug(
      f"Features built for segment {segment_id}: "
      f"weather_risk={weather_risk:.2f}, "
      f"speed_mean={stats.get('speed_mean', 0):.1f}, "
      f"sequence_length={len(seq)}"
    )
  
  return normalized


def forward_to_features(msg: Dict[str, Any]) -> None:
  producer: KafkaProducer | None = _make_producer()
  if producer is None:
    return
  enriched = build_features(msg)
  producer.send(config.FEATURES_TOPIC, enriched)
  producer.flush()
