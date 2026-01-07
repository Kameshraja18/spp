from fastapi import APIRouter, HTTPException

from services.api.schemas import IngestRequest
from services.stream.producer import enqueue_traffic_records

router = APIRouter()


@router.post("", summary="Receive streaming traffic and weather data and push to Kafka")
async def ingest(payload: IngestRequest) -> dict:
    try:
        await enqueue_traffic_records(payload.traffic_records)
        return {"status": "accepted", "count": len(payload.traffic_records)}
    except Exception as exc:  # pragma: no cover - surfacing unexpected issues
        raise HTTPException(status_code=500, detail=str(exc)) from exc
