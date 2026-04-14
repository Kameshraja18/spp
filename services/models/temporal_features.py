"""Temporal feature engineering for traffic predictions."""

from datetime import datetime
import numpy as np


def extract_temporal_features(timestamp_str: str) -> dict:
    """Extract temporal features from ISO datetime string.
    
    Args:
        timestamp_str: ISO format datetime string (e.g., "2023-01-01 08:00:00")
    
    Returns:
        Dict with temporal features:
        - hour: 0-23
        - day_of_week: 0-6 (Monday=0, Sunday=6)
        - day_of_month: 1-31
        - month: 1-12
        - is_weekend: 0/1
        - is_peak_hour: 0/1 (rush hour 7-9am, 5-7pm)
        - hour_sin/cos: cyclic encoding of hour
        - day_sin/cos: cyclic encoding of day
        - time_to_peak: minutes until next peak hour
    """
    dt = datetime.fromisoformat(timestamp_str.replace(" ", "T") if " " in timestamp_str else timestamp_str)
    
    hour = dt.hour
    day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
    day_of_month = dt.day
    month = dt.month
    
    # Boolean features
    is_weekend = 1 if day_of_week >= 5 else 0
    is_peak_hour = 1 if hour in [7, 8, 17, 18] else 0  # Rush hours
    
    # Cyclic encoding for hour (0-23 normalized to 0-2π)
    hour_rad = (hour / 24.0) * 2 * np.pi
    hour_sin = float(np.sin(hour_rad))
    hour_cos = float(np.cos(hour_rad))
    
    # Cyclic encoding for day of month (1-31 normalized to 0-2π)
    day_rad = ((day_of_month - 1) / 31.0) * 2 * np.pi
    day_sin = float(np.sin(day_rad))
    day_cos = float(np.cos(day_rad))
    
    # Time to next peak hour
    peak_hours = [7, 17]  # Morning and evening peaks
    time_to_peak = _minutes_to_next_peak(hour, minute=dt.minute, peak_hours=peak_hours)
    
    return {
        "hour": hour,
        "day_of_week": day_of_week,
        "day_of_month": day_of_month,
        "month": month,
        "is_weekend": is_weekend,
        "is_peak_hour": is_peak_hour,
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_sin": day_sin,
        "day_cos": day_cos,
        "time_to_peak_minutes": time_to_peak,
    }


def _minutes_to_next_peak(hour: int, minute: int, peak_hours: list) -> int:
    """Calculate minutes until next peak hour.
    
    Args:
        hour: Current hour (0-23)
        minute: Current minute (0-59)
        peak_hours: List of peak hours (e.g., [7, 17])
    
    Returns:
        Minutes to next peak hour (0-1440)
    """
    current_minutes = hour * 60 + minute
    
    for peak_hour in peak_hours:
        peak_minutes = peak_hour * 60
        if peak_minutes > current_minutes:
            return peak_minutes - current_minutes
    
    # Next peak is tomorrow
    return 24 * 60 - current_minutes + peak_hours[0] * 60


def get_seasonal_risk_factor(timestamp_str: str) -> float:
    """Compute seasonal risk multiplier.
    
    Returns value in [1.0, 1.5] where:
    - 1.0 = safe season (summer, clear weather typical)
    - 1.5 = high-risk season (winter, snow/ice likely)
    """
    dt = datetime.fromisoformat(timestamp_str.replace(" ", "T") if " " in timestamp_str else timestamp_str)
    month = dt.month
    
    # Winter months (Dec, Jan, Feb) = higher risk
    if month in [12, 1, 2]:
        return 1.4
    # Shoulder months (Nov, Mar) = moderate risk
    elif month in [11, 3]:
        return 1.2
    # Spring/summer (Apr-Oct) = baseline
    else:
        return 1.0


def get_time_of_day_category(hour: int) -> str:
    """Categorize hour into day part.
    
    Returns: 'night', 'early_morning', 'morning_peak', 'daytime', 'evening_peak', 'evening'
    """
    if hour < 5:
        return "night"
    elif hour < 7:
        return "early_morning"
    elif hour < 10:
        return "morning_peak"
    elif hour < 17:
        return "daytime"
    elif hour < 19:
        return "evening_peak"
    else:
        return "evening"
