from __future__ import annotations

import json
from typing import Iterable

from kafka import KafkaProducer

from services.api.schemas import TrafficRecord
from services.stream import config

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer | None:
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception:
            return None
    return _producer


async def enqueue_traffic_records(records: Iterable[TrafficRecord]) -> None:
    producer = _get_producer()
    if producer is None:
        # If Kafka is unavailable, just drop messages to keep API responsive.
        return

    for rec in records:
        payload = rec.model_dump()
        producer.send(config.TRAFFIC_TOPIC, payload)
    producer.flush()
