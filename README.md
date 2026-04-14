# road_accident_prediction_rf_lstm_advanced

Starter scaffold for real-time road accident risk and severity prediction using FastAPI, Kafka, PostgreSQL, Redis, PyTorch LSTM, scikit-learn Random Forest, and SHAP for explainability.

## Mission & Ethics
- Mission: deliver timely, actionable road safety intelligence to operators and drivers while keeping human oversight central.
- Ethics: privacy-respecting data use, transparent limitations, and human-in-the-loop responses.
- Predictions are advisory only and must support, not replace, standard road safety rules and human judgment.

## Model Roles (Two Brains)
- LSTM risk model = early-warning brain: sequence-driven risk to surface near-term hazards.
- Random Forest severity model = severity brain: tabular severity classification to rank likely impact.

## Layout
- services/api: FastAPI app and routers (ingest, risk, severity, explain)
- services/models: Inference stubs for LSTM, RF, and SHAP (replace with real models)
- services/models/training: Train scripts for RF (tabular) and LSTM (sequence)
- services/stream: Kafka producers/placeholders
- docker-compose.yml: Kafka + Zookeeper + Postgres + Redis + API
- Dockerfile: API image build

Environment variables:
- `LSTM_MODEL_PATH`: path to a Torch state_dict for the LSTM risk model (optional; falls back to default weights).
- `RF_MODEL_PATH`: path to a joblib artifact with a RandomForest classifier (optional; falls back to uniform probabilities).
- `REDIS_URL`: Redis connection string used for caching latest risk scores.
- `KAFKA_BOOTSTRAP_SERVERS`: bootstrap servers for Kafka (default `localhost:9092`).
- Topic overrides: `TRAFFIC_TOPIC`, `WEATHER_TOPIC`, `FEATURES_TOPIC`, `RISK_TOPIC`, `SEVERITY_TOPIC`.
- `POSTGRES_DSN`: Postgres DSN for persistence (severity_scores table).
	Tables: severity_scores, risk_scores (auto-created on API startup and pipeline init_tables).

## Training
- RF: `python services/models/training/train_rf.py data/your_tabular.csv --output artifacts/rf_model.joblib`
- LSTM: `python services/models/training/train_lstm.py data/your_sequences.csv --output artifacts/lstm_state_dict.pt`
- Dev placeholders (untrained): `python scripts/bootstrap_artifacts.py`

## Testing
- Run unit tests: `pytest`

## Streaming pipeline (scaffold)
- Producers publish traffic/weather to Kafka; see services/stream/producer.py.
- Pipeline threads start on FastAPI startup (best-effort; fail-open if Kafka absent) via services/api/main.py.
- Consumer scaffolding in services/stream/pipeline.py to wire feature builder and model scorers.
- Feature builder in services/stream/feature_builder.py normalizes messages, maintains a 12-point sliding window per segment, and adds simple rolling averages (speed, congestion); extend with real enrichment (traffic+weather join, richer stats).
- docker-compose mounts ./artifacts to /app/artifacts for model files and sets default model paths.
- Severity and risk scores are upserted to Postgres via services/storage/db.py (tables auto-created if missing; FastAPI startup calls db.init_tables).

## Quickstart (dev)
1) Install deps: `python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt`
2) Copy `.env.example` to `.env` and adjust paths/hosts as needed (docker-compose uses defaults).
3) Run API locally: `uvicorn services.api.main:app --reload`
4) Bring infra + API via Docker: `docker-compose up --build`
5) Open docs: http://localhost:8000/docs

## Next steps
- Enhance feature builder: join weather feed, add richer rolling stats (min/max/variance, deltas), and optional graph context.
- Train/plug real LSTM and RF artifacts; tune thresholds and class weights; consider GNN integration.
- Add integration tests for Kafka/Redis/Postgres pipeline (or mocks) and CI.
- Add monitoring/exporters for Prometheus and structured logging for ELK.
