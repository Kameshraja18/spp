from fastapi import APIRouter, HTTPException

from services.api.schemas import ExplainRequest, ExplainResponse
from services.models.inference import explain_instance

router = APIRouter()


@router.post("", response_model=ExplainResponse, summary="Explain model prediction with SHAP")
async def explain(payload: ExplainRequest) -> ExplainResponse:
    try:
        return await explain_instance(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
