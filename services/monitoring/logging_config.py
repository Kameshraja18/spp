"""ELK Stack (Elasticsearch, Logstash, Kibana) logging configuration."""

import logging
import json
from logging.handlers import SocketHandler
from pythonjsonlogger import jsonlogger
import os


class StructuredLogFormatter(jsonlogger.JsonFormatter):
    """Format logs as JSON for Elasticsearch ingestion."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


def setup_elasticsearch_logging(
    es_host: str = None,
    es_port: int = 9200,
    app_name: str = "road-accident-prediction",
) -> logging.Logger:
    """Setup logging to Elasticsearch via Logstash.
    
    Args:
        es_host: Elasticsearch host (default: env ELASTICSEARCH_HOST or localhost)
        es_port: Elasticsearch port (default: 9200)
        app_name: Application name for log tags
    
    Returns:
        Configured logger instance
    """
    es_host = es_host or os.getenv("ELASTICSEARCH_HOST", "localhost")
    logstash_host = os.getenv("LOGSTASH_HOST", "localhost")
    logstash_port = int(os.getenv("LOGSTASH_PORT", 5000))
    
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(console_handler)
    
    # Logstash handler (send logs to Logstash for processing)
    try:
        logstash_handler = SocketHandler(logstash_host, logstash_port)
        logstash_handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(logstash_handler)
    except Exception as e:
        logger.warning(f"Failed to connect to Logstash at {logstash_host}:{logstash_port}: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a module logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
    return logger


# Module-level loggers
inference_logger = get_logger("inference")
pipeline_logger = get_logger("pipeline")
storage_logger = get_logger("storage")
api_logger = get_logger("api")


class LogContext:
    """Context manager for structured logging with extra fields."""
    
    def __init__(self, logger: logging.Logger, **extra_fields):
        self.logger = logger
        self.extra_fields = extra_fields
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra={**self.extra_fields, **kwargs})
    
    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra={**self.extra_fields, **kwargs})
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra={**self.extra_fields, **kwargs})
    
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra={**self.extra_fields, **kwargs})
