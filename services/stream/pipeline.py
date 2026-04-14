"""Kafka pipeline scaffolding for streaming path.

Flow:
1) Producers publish traffic_raw/weather_raw.
2) Feature builder consumes, enriches, and emits features_enriched.
3) Risk scorer consumes, runs LSTM, emits risk_scored, caches Redis.
4) Severity scorer consumes, injects latest risk, runs RF, emits severity_scored, writes sinks.

This module provides topic constants and placeholders for consumer loops.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Callable, Optional

from kafka import KafkaConsumer, KafkaProducer

from services.api.schemas import RiskPredictionRequest, SeverityPredictionRequest
from services.models import inference
from services.stream import config
from services.storage import cache, db

_producer: Optional[KafkaProducer] = None


def _make_consumer(topic: str, group_id: str) -> KafkaConsumer | None:
    try:
        return KafkaConsumer(
            topic,
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
    except Exception:
        return None


def _make_producer() -> KafkaProducer | None:
    global _producer
    if _producer:
        return _producer
    try:
        _producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        return _producer
    except Exception:
        return None


def _start_loop(consumer: KafkaConsumer, handler: Callable[[dict], None], name: str):
    def run():
        for message in consumer:
            try:
                handler(message.value)
            except Exception:
                continue

    thread = threading.Thread(target=run, name=name, daemon=True)
    thread.start()
    return thread


def start_feature_builder(handler: Callable[[dict], None]) -> None:
    consumer = _make_consumer(config.TRAFFIC_TOPIC, group_id="feature-builder")
    if consumer:
        _start_loop(consumer, handler, name="feature-builder")


def start_risk_scorer() -> None:
    consumer = _make_consumer(config.FEATURES_TOPIC, group_id="risk-scorer")
    producer = _make_producer()
    if not consumer or not producer:
        return

    async def handle(msg: dict):
        req = RiskPredictionRequest.model_validate(msg)
        resp = await inference.predict_risk(req)
        producer.send(config.RISK_TOPIC, resp.model_dump())
        producer.flush()
        db.upsert_risk_score(
            {
                "road_segment_id": resp.road_segment_id,
                "risk_score": resp.risk_score,
                "risk_label": resp.risk_label,
                "prediction_horizon_min": resp.prediction_horizon_min,
            }
        )

    def wrapper(message: dict):
        asyncio.run(handle(message))

    _start_loop(consumer, wrapper, name="risk-scorer")


def start_severity_scorer() -> None:
    consumer = _make_consumer(config.RISK_TOPIC, group_id="severity-scorer")
    producer = _make_producer()
    if not consumer or not producer:
        return

    async def handle(msg: dict):
        # Risk message should already contain risk_score; stash to cache for API reuse.
        road_segment_id = msg.get("road_segment_id")
        risk_score = msg.get("risk_score")
        if road_segment_id and risk_score is not None:
            cache.set_latest_risk(road_segment_id, float(risk_score))

        req = SeverityPredictionRequest.model_validate(msg)
        resp = await inference.predict_severity(req)
        producer.send(config.SEVERITY_TOPIC, resp.model_dump())
        producer.flush()
        db.upsert_severity_score(
            {
                "road_segment_id": road_segment_id,
                "severity_class": resp.severity_class,
                "severity_label": resp.severity_label,
                "no_injury": resp.probabilities.no_injury,
                "minor": resp.probabilities.minor,
                "serious": resp.probabilities.serious,
                "fatal": resp.probabilities.fatal,
            }
        )

    def wrapper(message: dict):
        asyncio.run(handle(message))

    _start_loop(consumer, wrapper, name="severity-scorer")


def start_pipeline(feature_handler: Callable[[dict], None] | None = None) -> None:
    if feature_handler:
        start_feature_builder(feature_handler)
    start_risk_scorer()
    start_severity_scorer()
