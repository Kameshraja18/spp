from services.stream import pipeline


def test_make_producer_no_kafka(monkeypatch):
    # Force bootstrap servers to unreachable to ensure graceful None.
    monkeypatch.setattr(pipeline.config, "KAFKA_BOOTSTRAP_SERVERS", "localhost:65534")
    producer = pipeline._make_producer()
    assert producer is None


def test_make_consumer_no_kafka(monkeypatch):
    monkeypatch.setattr(pipeline.config, "KAFKA_BOOTSTRAP_SERVERS", "localhost:65534")
    consumer = pipeline._make_consumer("topic", group_id="g1")
    assert consumer is None
