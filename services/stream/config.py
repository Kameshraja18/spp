import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TRAFFIC_TOPIC = os.getenv("TRAFFIC_TOPIC", "traffic_raw")
WEATHER_TOPIC = os.getenv("WEATHER_TOPIC", "weather_raw")
FEATURES_TOPIC = os.getenv("FEATURES_TOPIC", "features_enriched")
RISK_TOPIC = os.getenv("RISK_TOPIC", "risk_scored")
SEVERITY_TOPIC = os.getenv("SEVERITY_TOPIC", "severity_scored")
