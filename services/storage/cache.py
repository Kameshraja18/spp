from __future__ import annotations

import os
from typing import Optional

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_client: Optional[redis.Redis] = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def set_latest_risk(road_segment_id: str, risk_score: float, ttl_seconds: int = 300) -> None:
    try:
        client = _get_client()
        client.set(f"risk:{road_segment_id}", risk_score, ex=ttl_seconds)
    except Exception:
        # Cache failures should not break API paths.
        pass


def get_latest_risk(road_segment_id: str) -> Optional[float]:
    try:
        client = _get_client()
        val = client.get(f"risk:{road_segment_id}")
        return float(val) if val is not None else None
    except Exception:
        return None
