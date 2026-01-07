from typing import List

import numpy as np

from services.api.schemas import (
    ExplainRequest,
    ExplainResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
    SHAPValue,
    SeverityPredictionRequest,
    SeverityPredictionResponse,
    SeverityProbabilities,
)
from services.models import features
from services.models.model_registry import get_lstm_model, get_rf_model
from services.models.utils import risk_label_from_score, severity_label_from_idx
from services.storage import cache


async def predict_risk(payload: RiskPredictionRequest) -> RiskPredictionResponse:
    model = get_lstm_model()
    if model is None:
        # Safe fallback if the LSTM artifact is missing.
        risk_score = 0.5
    else:
        sequence_tensor = features.sequence_to_tensor(payload.recent_sequence)
        risk_score = float(model.predict_score(sequence_tensor))

    risk_label = risk_label_from_score(risk_score)
    cache.set_latest_risk(payload.road_segment_id, risk_score)
    return RiskPredictionResponse(
        road_segment_id=payload.road_segment_id,
        risk_score=risk_score,
        risk_label=risk_label,
        prediction_horizon_min=15,
    )


async def predict_severity(payload: SeverityPredictionRequest) -> SeverityPredictionResponse:
    model = get_rf_model()
    if payload.lstm_risk_score is None:
        cached = cache.get_latest_risk(payload.road_segment_id)
        if cached is not None:
            payload = payload.model_copy(update={"lstm_risk_score": cached})

    x, feature_names = features.build_severity_features(payload)

    if model is None:
        # Evenly spread probability if the RF artifact is missing.
        prob_array = np.array([[0.25, 0.25, 0.25, 0.25]])
    else:
        prob_array = model.predict_proba(x)

    probs = SeverityProbabilities(
        no_injury=float(prob_array[0, 0]),
        minor=float(prob_array[0, 1]),
        serious=float(prob_array[0, 2]),
        fatal=float(prob_array[0, 3]),
    )
    class_idx = int(np.argmax(prob_array[0]))
    return SeverityPredictionResponse(
        severity_class=class_idx,
        severity_label=severity_label_from_idx(class_idx),
        probabilities=probs,
    )


async def explain_instance(payload: ExplainRequest) -> ExplainResponse:
    rf_model = get_rf_model()
    if rf_model is None:
        shap_values: List[SHAPValue] = [
            SHAPValue(feature="avg_speed_current", contribution=0.1),
            SHAPValue(feature="weather_Rain", contribution=0.05),
        ]
        suggestions = [
            "Reduce speed on rainy segments.",
            "Improve lighting on dark segments.",
        ]
        return ExplainResponse(
            shap_values=shap_values,
            top_features=[sv.feature for sv in shap_values],
            counterfactual_suggestions=suggestions,
        )

    try:
        import shap
    except Exception:
        # If SHAP fails to import in the environment, degrade gracefully.
        shap_values: List[SHAPValue] = [
            SHAPValue(feature="model_bias", contribution=0.0),
        ]
        return ExplainResponse(
            shap_values=shap_values,
            top_features=[sv.feature for sv in shap_values],
            counterfactual_suggestions=["Install shap for detailed explanations."],
        )

    x, feature_names = features.build_explain_features(payload.instance)
    explainer = shap.TreeExplainer(rf_model.model)
    shap_raw = explainer.shap_values(x)
    # For multiclass, shap returns list; take mean absolute contributions across classes.
    if isinstance(shap_raw, list):
        shap_mean = np.mean(np.abs(np.stack(shap_raw, axis=0)), axis=0)[0]
    else:
        shap_mean = np.abs(shap_raw)[0]

    scored = list(zip(feature_names, shap_mean))
    scored.sort(key=lambda t: t[1], reverse=True)
    shap_values: List[SHAPValue] = [
        SHAPValue(feature=name, contribution=float(val)) for name, val in scored[:8]
    ]
    suggestions = features.counterfactual_hints(scored)
    return ExplainResponse(
        shap_values=shap_values,
        top_features=[sv.feature for sv in shap_values],
        counterfactual_suggestions=suggestions,
    )
