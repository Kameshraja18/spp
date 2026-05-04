from datetime import datetime
from typing import List, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator


def _to_python_datetime(value):
    """Convert str/np.datetime64/datetime to python datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, np.datetime64):
        # Convert numpy.datetime64 to seconds since epoch then to datetime
        ts = (value - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
        return datetime.utcfromtimestamp(float(ts))
    if isinstance(value, str):
        # Support both 'YYYY-MM-DD HH:MM:SS' and ISO strings
        try:
            return datetime.fromisoformat(value.replace(" ", "T") if " " in value else value)
        except Exception:
            return datetime.fromisoformat(value)
    return value


class TrafficRecord(BaseModel):
    timestamp: datetime
    road_segment_id: str
    avg_speed: float
    flow: float
    occupancy: float
    congestion_index: float

    @field_validator('timestamp', mode='before')
    def _validate_timestamp(cls, v):
        return _to_python_datetime(v)


class IngestRequest(BaseModel):
    traffic_records: List[TrafficRecord]


class RiskSequencePoint(BaseModel):
    timestamp: datetime
    avg_speed: float
    flow: float
    occupancy: float
    congestion_index: float
    rain_intensity: float

    @field_validator('timestamp', mode='before')
    def _validate_timestamp(cls, v):
        return _to_python_datetime(v)


class RiskPredictionRequest(BaseModel):
    road_segment_id: str
    recent_sequence: List[RiskSequencePoint]


class RiskPredictionResponse(BaseModel):
    road_segment_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_label: Literal["LOW", "MEDIUM", "HIGH"]
    prediction_horizon_min: int


class SeverityPredictionRequest(BaseModel):
    road_segment_id: str
    timestamp: datetime
    weather: str
    light_condition: str
    road_type: str
    surface_condition: str
    avg_speed_current: float
    congestion_index_current: float
    lstm_risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    historical_accident_rate_segment: Optional[float] = Field(default=None, ge=0.0)

    @field_validator('timestamp', mode='before')
    def _validate_timestamp(cls, v):
        return _to_python_datetime(v)


class SeverityProbabilities(BaseModel):
    no_injury: float
    minor: float
    serious: float
    fatal: float


class SeverityPredictionResponse(BaseModel):
    severity_class: Literal[0, 1, 2, 3]
    severity_label: Literal["no_injury", "minor", "serious", "fatal"]
    probabilities: SeverityProbabilities


class ExplainRequest(BaseModel):
    model: Literal["random_forest_severity"]
    instance: dict


class SHAPValue(BaseModel):
    feature: str
    contribution: float


class ExplainResponse(BaseModel):
    shap_values: List[SHAPValue]
    top_features: List[str]
    counterfactual_suggestions: List[str]
