"""Advanced rolling statistics for traffic data."""

from collections import deque
from typing import List, Optional
import numpy as np


class RollingStats:
    """Compute rolling statistics over a sliding window."""
    
    def __init__(self, window_size: int = 12):
        self.window_size = window_size
        self.speed_window = deque(maxlen=window_size)
        self.congestion_window = deque(maxlen=window_size)
        self.flow_window = deque(maxlen=window_size)
    
    def update(self, speed: float, congestion: float, flow: float):
        """Add new observation to windows."""
        self.speed_window.append(speed)
        self.congestion_window.append(congestion)
        self.flow_window.append(flow)
    
    def get_stats(self) -> dict:
        """Compute all rolling statistics.
        
        Returns:
            Dict with keys:
            - speed_*: mean, std, min, max, delta (current - oldest)
            - congestion_*: mean, std, min, max, delta, trend
            - flow_*: mean, std, min, max
            - acceleration: (current_speed - prev_speed)
            - volatility: combined speed+congestion variance
        """
        if len(self.speed_window) == 0:
            return self._default_stats()
        
        speed_arr = np.array(self.speed_window)
        cong_arr = np.array(self.congestion_window)
        flow_arr = np.array(self.flow_window)
        
        # Speed stats (ENHANCED with variance, percentiles, rate of change)
        speed_stats = {
            "speed_mean": float(np.mean(speed_arr)),
            "speed_std": float(np.std(speed_arr)),
            "speed_min": float(np.min(speed_arr)),
            "speed_max": float(np.max(speed_arr)),
            "speed_variance": float(np.var(speed_arr)),  # NEW: variance
            "speed_range": float(np.max(speed_arr) - np.min(speed_arr)),  # NEW: range
            "speed_delta": float(speed_arr[-1] - speed_arr[0]),  # Change over window
            "speed_trend": float(np.polyfit(range(len(speed_arr)), speed_arr, 1)[0]) if len(speed_arr) > 1 else 0.0,  # Slope
            "speed_percentile_25": float(np.percentile(speed_arr, 25)),  # NEW: 25th percentile
            "speed_percentile_75": float(np.percentile(speed_arr, 75)),  # NEW: 75th percentile
            "speed_median": float(np.median(speed_arr)),  # NEW: median
        }
        
        # Congestion stats (ENHANCED)
        cong_stats = {
            "congestion_mean": float(np.mean(cong_arr)),
            "congestion_std": float(np.std(cong_arr)),
            "congestion_min": float(np.min(cong_arr)),
            "congestion_max": float(np.max(cong_arr)),
            "congestion_variance": float(np.var(cong_arr)),  # NEW: variance
            "congestion_range": float(np.max(cong_arr) - np.min(cong_arr)),  # NEW: range
            "congestion_delta": float(cong_arr[-1] - cong_arr[0]),
            "congestion_trend": float(np.polyfit(range(len(cong_arr)), cong_arr, 1)[0]) if len(cong_arr) > 1 else 0.0,
            "congestion_median": float(np.median(cong_arr)),  # NEW: median
        }
        
        # Flow stats (ENHANCED)
        flow_stats = {
            "flow_mean": float(np.mean(flow_arr)),
            "flow_std": float(np.std(flow_arr)),
            "flow_min": float(np.min(flow_arr)),
            "flow_max": float(np.max(flow_arr)),
            "flow_variance": float(np.var(flow_arr)),  # NEW: variance
            "flow_range": float(np.max(flow_arr) - np.min(flow_arr)),  # NEW: range
            "flow_median": float(np.median(flow_arr)),  # NEW: median
        }
        
        # Acceleration (recent vs previous)
        acceleration = 0.0
        if len(speed_arr) >= 2:
            acceleration = float(speed_arr[-1] - speed_arr[-2])
        
        # Volatility (combined variance indicator)
        combined = np.concatenate([
            (speed_arr - np.mean(speed_arr)) / (np.std(speed_arr) + 1e-6),
            (cong_arr - np.mean(cong_arr)) / (np.std(cong_arr) + 1e-6),
        ])
        volatility = float(np.std(combined))
        
        return {
            **speed_stats,
            **cong_stats,
            **flow_stats,
            "acceleration": acceleration,
            "volatility": volatility,
        }
    
    def _default_stats(self) -> dict:
        """Return default stats when window empty."""
        return {
            "speed_mean": 0.0, "speed_std": 0.0, "speed_min": 0.0, "speed_max": 0.0,
            "speed_delta": 0.0, "speed_trend": 0.0,
            "congestion_mean": 0.0, "congestion_std": 0.0, "congestion_min": 0.0,
            "congestion_max": 0.0, "congestion_delta": 0.0, "congestion_trend": 0.0,
            "flow_mean": 0.0, "flow_std": 0.0, "flow_min": 0.0, "flow_max": 0.0,
            "acceleration": 0.0, "volatility": 0.0,
        }


class TimeDecayWeightedAverage:
    """Compute time-decay weighted moving average (recent data weighted more)."""
    
    def __init__(self, decay_rate: float = 0.9):
        """decay_rate in (0, 1): higher = faster decay of old data."""
        self.decay_rate = decay_rate
        self.values = deque()
    
    def update(self, value: float):
        self.values.append(value)
    
    def compute(self) -> float:
        """Compute weighted average where recent values have higher weight."""
        if not self.values:
            return 0.0
        
        values_arr = np.array(list(self.values))
        n = len(values_arr)
        
        # Exponential weights: most recent = 1, oldest = decay_rate^(n-1)
        weights = np.array([self.decay_rate ** (n - 1 - i) for i in range(n)])
        weights = weights / weights.sum()  # Normalize
        
        return float(np.dot(weights, values_arr))
