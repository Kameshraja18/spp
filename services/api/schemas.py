from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TrafficRecord(BaseModel):
    timestamp: datetime
    road_segment_id: str
    avg_speed: float
    flow: float
    occupancy: float
    congestion_index: float


class IngestRequest(BaseModel):
    traffic_records: List[TrafficRecord]


class RiskSequencePoint(BaseModel):
    timestamp: datetime
    avg_speed: float
    flow: float
    occupancy: float
    congestion_index: float
    rain_intensity: float


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
