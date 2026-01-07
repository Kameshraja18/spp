from fastapi import APIRouter, HTTPException

from services.api.schemas import (
    SeverityPredictionRequest,
    SeverityPredictionResponse,
)
from services.models.inference import predict_severity

router = APIRouter()


@router.post("/severity", response_model=SeverityPredictionResponse, summary="Predict severity class for a potential accident")
async def predict_severity_endpoint(payload: SeverityPredictionRequest) -> SeverityPredictionResponse:
    try:
        return await predict_severity(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
