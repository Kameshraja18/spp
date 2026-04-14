from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from services.api.routers import ingest, risk, severity, explain, advanced
from services.storage import db
from services.stream import pipeline
from services.stream import feature_builder
from services.monitoring.metrics import REGISTRY


app = FastAPI(title="Road Accident Risk and Severity API")

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(risk.router, prefix="/predict", tags=["risk"])
app.include_router(severity.router, prefix="/predict", tags=["severity"])
app.include_router(explain.router, prefix="/explain", tags=["explain"])
app.include_router(advanced.router, tags=["advanced"])

app.mount("/ui", StaticFiles(directory="services/api/static", html=True), name="ui")


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "name": "Road Accident Risk and Severity API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "ui": "/ui",
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return JSONResponse(
        content=generate_latest(REGISTRY).decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.on_event("startup")
async def _startup() -> None:
    try:
        db.init_tables()
    except Exception:
        # Avoid blocking API startup on DB issues; logs can be added later.
        pass
    try:
        pipeline.start_pipeline(feature_handler=feature_builder.forward_to_features)
    except Exception:
        # Kafka may be unavailable in dev; fail open.
        pass

