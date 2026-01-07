"""Weather data service for feature enrichment.

Provides weather lookups and enrichment for traffic data.
In production, integrate with real weather API (WeatherAPI, OpenWeatherMap, etc).
Enhanced with road segment joins and richer weather attributes.
"""

from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ENHANCED: More comprehensive weather data with additional attributes
MOCK_WEATHER_DB = {
    ("S1", "2023-01-01 08:00:00"): {
        "temp": 5, "wind_speed": 10, "visibility": 10000,
        "humidity": 85, "precipitation": 0.0, "cloud_cover": 60, "condition": "cloudy"
    },
    ("S1", "2023-01-01 09:00:00"): {
        "temp": 4, "wind_speed": 15, "visibility": 5000,
        "humidity": 90, "precipitation": 2.0, "cloud_cover": 80, "condition": "rain"
    },
    ("S2", "2023-01-01 08:00:00"): {
        "temp": 3, "wind_speed": 20, "visibility": 3000,
        "humidity": 95, "precipitation": 5.0, "cloud_cover": 100, "condition": "heavy_rain"
    },
    ("S2", "2023-01-01 09:00:00"): {
        "temp": 2, "wind_speed": 25, "visibility": 2000,
        "humidity": 95, "precipitation": 8.0, "cloud_cover": 100, "condition": "storm"
    },
    ("S3", "2023-01-01 08:00:00"): {
        "temp": -2, "wind_speed": 30, "visibility": 1000,
        "humidity": 100, "precipitation": 0.5, "cloud_cover": 100, "condition": "snow"
    },
    # Add more mock data for various segments and times
    ("S42", "2026-01-05 20:00:00"): {
        "temp": 12, "wind_speed": 8, "visibility": 8000,
        "humidity": 70, "precipitation": 0.0, "cloud_cover": 30, "condition": "clear"
    },
    ("S18", "2026-01-05 20:00:00"): {
        "temp": 10, "wind_speed": 12, "visibility": 6000,
        "humidity": 80, "precipitation": 1.5, "cloud_cover": 70, "condition": "light_rain"
    },
}

# Default safe values for missing data (ENHANCED)
DEFAULT_WEATHER = {
    "temp": 15.0,
    "wind_speed": 5.0,
    "visibility": 10000.0,
    "humidity": 60.0,
    "precipitation": 0.0,
    "cloud_cover": 50,
    "condition": "clear",
}


def get_weather(road_segment_id: str, timestamp: str) -> dict:
    """Fetch weather data for segment at timestamp.
    
    Args:
        road_segment_id: Road segment identifier
        timestamp: ISO datetime string
    
    Returns:
        Dict with temp (°C), wind_speed (km/h), visibility (meters),
        humidity (%), precipitation (mm/h), cloud_cover (%), condition (str)
    """
    key = (road_segment_id, timestamp)
    weather = MOCK_WEATHER_DB.get(key, DEFAULT_WEATHER.copy())
    logger.debug(f"Weather lookup for {key}: {weather}")
    return weather


def enrich_features_with_weather(features: dict, road_segment_id: str, timestamp: str) -> dict:
    """Add weather features to feature dict (ENHANCED).
    
    Args:
        features: Feature dictionary to enrich
        road_segment_id: Segment ID
        timestamp: ISO timestamp
    
    Returns:
        Enriched features dict with weather keys including:
        - temperature, wind_speed, visibility (original)
        - humidity, precipitation, cloud_cover, condition (new)
        - weather_risk_factor (computed)
    """
    weather = get_weather(road_segment_id, timestamp)
    features.update({
        "temperature": weather["temp"],
        "wind_speed": weather["wind_speed"],
        "visibility": weather["visibility"],
        "humidity": weather.get("humidity", 60.0),  # NEW
        "precipitation": weather.get("precipitation", 0.0),  # NEW
        "cloud_cover": weather.get("cloud_cover", 50),  # NEW
        "weather_condition": weather.get("condition", "clear"),  # NEW
        "weather_risk_factor": compute_weather_risk_factor(weather),  # Add computed risk
    })
    return features


def compute_weather_risk_factor(weather: dict) -> float:
    """Compute risk multiplier based on weather conditions (ENHANCED).
    
    Returns value in [1.0, 3.0] where:
    - 1.0 = good conditions (high visibility, low wind, warm, dry)
    - 3.0 = severe conditions (low visibility, high wind, cold, heavy precipitation)
    """
    risk = 1.0
    
    # Visibility (inverse: lower visibility = higher risk)
    if weather["visibility"] < 1000:
        risk *= 2.5
    elif weather["visibility"] < 3000:
        risk *= 2.0
    elif weather["visibility"] < 5000:
        risk *= 1.5
    
    # Wind speed
    if weather["wind_speed"] > 50:
        risk *= 2.0
    elif weather["wind_speed"] > 40:
        risk *= 1.8
    elif weather["wind_speed"] > 25:
        risk *= 1.3
    
    # Temperature (cold = higher risk)
    if weather["temp"] < -5:
        risk *= 1.6
    elif weather["temp"] < 0:
        risk *= 1.4
    elif weather["temp"] < 5:
        risk *= 1.2
    
    # NEW: Precipitation (rain/snow)
    precip = weather.get("precipitation", 0.0)
    if precip > 10:  # Heavy rain/snow (>10mm/h)
        risk *= 1.8
    elif precip > 5:  # Moderate
        risk *= 1.4
    elif precip > 1:  # Light
        risk *= 1.2
    
    # NEW: Humidity (fog risk at high humidity)
    humidity = weather.get("humidity", 60.0)
    if humidity > 95:
        risk *= 1.3
    elif humidity > 85:
        risk *= 1.1
    
    return min(risk, 3.0)
