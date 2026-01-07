from fastapi import APIRouter, HTTPException

from services.api.schemas import RiskPredictionRequest, RiskPredictionResponse
from services.models.inference import predict_risk

router = APIRouter()


@router.post("/risk", response_model=RiskPredictionResponse, summary="Return short-term accident risk for a road segment")
async def predict_risk_endpoint(payload: RiskPredictionRequest) -> RiskPredictionResponse:
    try:
        return await predict_risk(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
