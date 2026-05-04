from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from services.api.routers import ingest, risk, severity, explain, advanced
from services.api.routers import auth as auth_router
from services.api.auth import decode_access_token
from services.storage import db
from services.storage import auth as auth_storage
from services.stream import pipeline
from services.stream import feature_builder
from services.monitoring.metrics import REGISTRY


app = FastAPI(title="Road Accident Risk and Severity API")

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(risk.router, prefix="/predict", tags=["risk"])
app.include_router(severity.router, prefix="/predict", tags=["severity"])
app.include_router(explain.router, prefix="/explain", tags=["explain"])
app.include_router(advanced.router, tags=["advanced"])
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])

STATIC_DIR = Path("services/api/static")
UI_PAGE = STATIC_DIR / "index.html"
LOGIN_PAGE = STATIC_DIR / "login.html"


@app.get("/", tags=["root"])
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui", status_code=307)


@app.get("/login", tags=["auth"])
def login_page() -> FileResponse:
    return FileResponse(LOGIN_PAGE)


@app.get("/ui", tags=["ui"])
@app.get("/ui/", tags=["ui"])
def ui_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=307)

    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username or not auth_storage.user_exists(username):
            return RedirectResponse(url="/login", status_code=307)
    except Exception:
        return RedirectResponse(url="/login", status_code=307)

    return FileResponse(UI_PAGE)


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

