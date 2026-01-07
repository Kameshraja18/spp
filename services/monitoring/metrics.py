"""Prometheus metrics for monitoring model performance and system health.

ENHANCED with Kafka, Redis, feature engineering metrics and structured logging.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time
import logging
from functools import wraps

# Configure structured logging
logger = logging.getLogger(__name__)

# Create custom registry
REGISTRY = CollectorRegistry()

# Counters
prediction_counter = Counter(
    'predictions_total',
    'Total number of predictions made',
    ['model_type', 'endpoint'],
    registry=REGISTRY,
)

errors_counter = Counter(
    'prediction_errors_total',
    'Total number of prediction errors',
    ['error_type'],
    registry=REGISTRY,
)

cache_hits_counter = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['key_type'],
    registry=REGISTRY,
)

cache_misses_counter = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['key_type'],
    registry=REGISTRY,
)

# NEW: Kafka metrics
kafka_messages_sent = Counter(
    'kafka_messages_sent_total',
    'Total messages sent to Kafka',
    ['topic'],
    registry=REGISTRY,
)

kafka_messages_received = Counter(
    'kafka_messages_received_total',
    'Total messages received from Kafka',
    ['topic'],
    registry=REGISTRY,
)

kafka_errors = Counter(
    'kafka_errors_total',
    'Total Kafka connection/send errors',
    ['error_type'],
    registry=REGISTRY,
)

# NEW: Feature engineering metrics
feature_enrichments = Counter(
    'feature_enrichments_total',
    'Total feature enrichment operations',
    ['enrichment_type'],
    registry=REGISTRY,
)

weather_api_calls = Counter(
    'weather_api_calls_total',
    'Total weather service API calls',
    ['status'],
    registry=REGISTRY,
)

rolling_stats_computed = Counter(
    'rolling_stats_computed_total',
    'Total rolling statistics computations',
    ['stat_type'],
    registry=REGISTRY,
)

# Histograms
prediction_latency = Histogram(
    'prediction_latency_seconds',
    'Prediction latency in seconds',
    ['model_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

db_latency = Histogram(
    'db_operation_latency_seconds',
    'Database operation latency',
    ['operation'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0),
    registry=REGISTRY,
)

# NEW: Kafka latency
kafka_send_latency = Histogram(
    'kafka_send_latency_seconds',
    'Kafka message send latency',
    ['topic'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5),
    registry=REGISTRY,
)

# NEW: Feature enrichment latency
feature_enrichment_latency = Histogram(
    'feature_enrichment_latency_seconds',
    'Feature enrichment pipeline latency',
    ['enrichment_type'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1),
    registry=REGISTRY,
)

# NEW: Redis operation latency
redis_operation_latency = Histogram(
    'redis_operation_latency_seconds',
    'Redis operation latency',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1),
    registry=REGISTRY,
)

# Gauges
model_accuracy = Gauge(
    'model_accuracy',
    'Current model accuracy on validation set',
    ['model_type'],
    registry=REGISTRY,
)

model_drift_score = Gauge(
    'model_drift_score',
    'Model drift detection score (0-1)',
    ['model_type'],
    registry=REGISTRY,
)

active_segments = Gauge(
    'active_road_segments',
    'Number of active road segments being monitored',
    registry=REGISTRY,
)

pending_predictions = Gauge(
    'pending_predictions',
    'Number of predictions in queue',
    registry=REGISTRY,
)

# NEW: Kafka consumer lag
kafka_consumer_lag = Gauge(
    'kafka_consumer_lag',
    'Kafka consumer lag by topic',
    ['topic', 'partition'],
    registry=REGISTRY,
)

# NEW: Weather data freshness
weather_data_age_seconds = Gauge(
    'weather_data_age_seconds',
    'Age of cached weather data in seconds',
    ['segment_id'],
    registry=REGISTRY,
)

# NEW: Feature statistics
feature_value_gauge = Gauge(
    'feature_value',
    'Current feature values for monitoring',
    ['feature_name', 'segment_id'],
    registry=REGISTRY,
)


def track_prediction_latency(model_type: str):
    """Decorator to track prediction latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                prediction_latency.labels(model_type=model_type).observe(duration)
                prediction_counter.labels(model_type=model_type, endpoint=func.__name__).inc()
        return wrapper
    return decorator


def track_db_operation(operation: str):
    """Decorator to track database operation latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                errors_counter.labels(error_type=type(e).__name__).inc()
                raise
            finally:
                duration = time.time() - start
                db_latency.labels(operation=operation).observe(duration)
        return wrapper
    return decorator


def record_cache_hit(key_type: str):
    """Record a cache hit."""
    cache_hits_counter.labels(key_type=key_type).inc()


def record_cache_miss(key_type: str):
    """Record a cache miss."""
    cache_misses_counter.labels(key_type=key_type).inc()


def update_model_accuracy(model_type: str, accuracy: float):
    """Update model accuracy metric."""
    model_accuracy.labels(model_type=model_type).set(accuracy)


def update_model_drift(model_type: str, drift_score: float):
    """Update model drift detection score."""
    model_drift_score.labels(model_type=model_type).set(min(max(drift_score, 0), 1))


def update_active_segments(count: int):
    """Update count of active segments."""
    active_segments.set(count)


def update_pending_predictions(count: int):
    """Update pending predictions queue size."""
    pending_predictions.set(count)


# NEW: Kafka tracking functions
def record_kafka_message_sent(topic: str):
    """Record a Kafka message sent."""
    kafka_messages_sent.labels(topic=topic).inc()
    logger.debug(f"Kafka message sent to topic: {topic}")


def record_kafka_message_received(topic: str):
    """Record a Kafka message received."""
    kafka_messages_received.labels(topic=topic).inc()


def record_kafka_error(error_type: str):
    """Record a Kafka error."""
    kafka_errors.labels(error_type=error_type).inc()
    logger.error(f"Kafka error: {error_type}")


def track_kafka_send(topic: str):
    """Decorator to track Kafka message send latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                record_kafka_message_sent(topic)
                return result
            except Exception as e:
                record_kafka_error(type(e).__name__)
                raise
            finally:
                duration = time.time() - start
                kafka_send_latency.labels(topic=topic).observe(duration)
        return wrapper
    return decorator


# NEW: Feature enrichment tracking
def record_feature_enrichment(enrichment_type: str):
    """Record a feature enrichment operation."""
    feature_enrichments.labels(enrichment_type=enrichment_type).inc()


def record_weather_api_call(status: str):
    """Record a weather API call (success or failure)."""
    weather_api_calls.labels(status=status).inc()


def record_rolling_stats_computation(stat_type: str):
    """Record rolling statistics computation."""
    rolling_stats_computed.labels(stat_type=stat_type).inc()


def track_feature_enrichment(enrichment_type: str):
    """Decorator to track feature enrichment latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                record_feature_enrichment(enrichment_type)
                return result
            except Exception as e:
                errors_counter.labels(error_type=type(e).__name__).inc()
                logger.error(f"Feature enrichment error ({enrichment_type}): {e}")
                raise
            finally:
                duration = time.time() - start
                feature_enrichment_latency.labels(enrichment_type=enrichment_type).observe(duration)
        return wrapper
    return decorator


# NEW: Redis tracking
def track_redis_operation(operation: str):
    """Decorator to track Redis operation latency."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    record_cache_hit(operation)
                else:
                    record_cache_miss(operation)
                return result
            except Exception as e:
                errors_counter.labels(error_type=type(e).__name__).inc()
                logger.error(f"Redis operation error ({operation}): {e}")
                raise
            finally:
                duration = time.time() - start
                redis_operation_latency.labels(operation=operation).observe(duration)
        return wrapper
    return decorator


def update_kafka_consumer_lag(topic: str, partition: int, lag: int):
    """Update Kafka consumer lag metric."""
    kafka_consumer_lag.labels(topic=topic, partition=str(partition)).set(lag)


def update_weather_data_age(segment_id: str, age_seconds: float):
    """Update weather data age metric."""
    weather_data_age_seconds.labels(segment_id=segment_id).set(age_seconds)


def update_feature_value(feature_name: str, segment_id: str, value: float):
    """Update feature value gauge for monitoring."""
    feature_value_gauge.labels(feature_name=feature_name, segment_id=segment_id).set(value)
