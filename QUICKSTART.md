# Quick Start Guide: Road Accident Prediction System

- Mission: deliver timely, actionable road safety intelligence with human oversight.
- Ethics: privacy-respecting data, transparent limits, and human-in-the-loop actions. Predictions are advisory only and must support, not replace, standard road safety rules and human judgment.
- Model roles: LSTM risk model = early-warning brain; Random Forest severity model = severity brain.

## 1️⃣ Start the API Server (Development)

```powershell
cd C:\spp
uvicorn services.api.main:app --reload
```

Access at: **http://localhost:8000/docs** (Swagger UI)

---

## 2️⃣ Start the Full Stack (Production + Monitoring)

```bash
docker-compose up --build
```

### Services Available:
| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | Main prediction API |
| Docs | http://localhost:8000/docs | Interactive API explorer |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |
| Kibana | http://localhost:5601 | Log visualization |
| Prometheus | http://localhost:9090 | Metrics scraping |

---

## 3️⃣ Test Endpoints

### Single Risk Prediction
```bash
curl -X POST "http://localhost:8000/predict/risk" \
  -H "Content-Type: application/json" \
  -d '{
    "road_segment_id": "S1",
    "recent_sequence": [
      {
        "timestamp": "2024-01-01T08:00:00",
        "avg_speed": 50,
        "flow": 100,
        "occupancy": 0.5,
        "congestion_index": 0.6,
        "rain_intensity": 0.2,
        "time_of_day_sin": 0.5,
        "time_of_day_cos": 0.866
      }
    ]
  }'
```

### Batch Risk Predictions
```bash
curl -X POST "http://localhost:8000/api/v2/predict/batch-risk" \
  -H "Content-Type: application/json" \
  -d '{
    "predictions": [
      {"road_segment_id": "S1", "recent_sequence": [...]},
      {"road_segment_id": "S2", "recent_sequence": [...]}
    ]
  }'
```

### Forecast Risk (Next 24 hours)
```bash
curl -X POST "http://localhost:8000/api/v2/forecast/risk" \
  -H "Content-Type: application/json" \
  -d '{
    "road_segment_id": "S1",
    "forecast_hours": 24
  }'
```

### Check Model Drift
```bash
curl -X POST "http://localhost:8000/api/v2/monitoring/drift-detection" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "risk"}'
```

### Get Model Performance Stats
```bash
curl "http://localhost:8000/api/v2/monitoring/performance/risk"
```

### Top-10 Critical Spots Tonight
```bash
curl "http://localhost:8000/api/v2/reports/critical-spots"
```

### Map-Ready Critical Spots (colors + reasons + actions)
```bash
curl "http://localhost:8000/api/v2/maps/critical-spots"
```

### Monthly Hotspot Report (Planners)
```bash
curl "http://localhost:8000/api/v2/reports/hotspots/monthly?month=2025-12"
```

### View Prometheus Metrics
```bash
curl "http://localhost:8000/metrics" | head -20
```

---

## 4️⃣ Key API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/ingest` | Send traffic records |
| POST | `/predict/risk` | Predict accident risk (LSTM) |
| POST | `/predict/severity` | Predict accident severity (RF) |
| POST | `/explain` | Get SHAP explanations |
| POST | `/api/v2/predict/batch-risk` | **Batch predictions** |
| POST | `/api/v2/forecast/risk` | **Risk forecasting** |
| GET | `/api/v2/alerts/rules` | **List alert rules** |
| POST | `/api/v2/alerts/rules` | **Create alert rule** |
| POST | `/api/v2/monitoring/drift-detection` | **Detect model drift** |
| GET | `/api/v2/monitoring/performance/{type}` | **Model performance** |
| GET | `/api/v2/reports/critical-spots` | **Top-10 critical spots tonight (reasons + actions)** |
| GET | `/api/v2/maps/critical-spots` | **Map-ready critical spots (segment, risk, color)** |
| GET | `/api/v2/reports/hotspots/monthly` | **Monthly hotspot report stub for planners** |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

---

## 5️⃣ Monitor System

### Kibana (Logs)
1. Open http://localhost:5601
2. Create index pattern: `road-accident-logs-*`
3. View real-time logs from Logstash

### Prometheus (Metrics)
1. Open http://localhost:9090
2. Query examples:
   - `predictions_total` – Total predictions made
   - `prediction_latency_seconds` – P95 latency
   - `model_drift_score` – Drift detection score
   - `cache_hits_total` – Cache effectiveness

### Grafana (Optional - requires separate setup)
```bash
# In docker-compose.yml, add:
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin
```

---

## 6️⃣ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: services` | Run from C:\spp directory |
| NumPy/PyTorch error | `pip install "numpy<2"` |
| Kafka unavailable | API starts anyway (fail-open), check docker logs |
| Elasticsearch connection error | Check `ELASTICSEARCH_HOST` in .env |
| Port 8000 already in use | `netstat -ano \| findstr :8000` then kill process |

---

## 7️⃣ Retrain Models

### Random Forest (Severity)
```bash
python services/models/training/train_rf.py data/tabular_severity.csv --output artifacts/rf_model.joblib
```

### LSTM (Risk)
```bash
python services/models/training/train_lstm.py data/sequences_lstm.csv --output artifacts/lstm_state_dict.pt --epochs 10
```

---

## 8️⃣ Feature Enrichment

The system automatically enriches predictions with:
- ✅ **Weather**: temperature, wind_speed, visibility, weather_risk_factor
- ✅ **Temporal**: hour, day_of_week, is_peak_hour, hour_sin/cos, seasonal_risk
- ✅ **Rolling Stats**: speed mean/std/trend, congestion delta, acceleration, volatility

All computed automatically in `services/stream/feature_builder.py`

---

## 9️⃣ Environment Variables

Create `.env` file (optional override):
```env
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/accidents
REDIS_URL=redis://redis:6379/0
LSTM_MODEL_PATH=/app/artifacts/lstm_state_dict.pt
RF_MODEL_PATH=/app/artifacts/rf_model.joblib
ELASTICSEARCH_HOST=elasticsearch
LOGSTASH_HOST=logstash
LOGSTASH_PORT=5000
```

---

## 🔟 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
│  (/docs, /health, /metrics, /api/v2/*)                     │
├─────────────────────────────────────────────────────────────┤
│  Routers:                                                   │
│  - ingest (Kafka producer)                                  │
│  - risk (LSTM predictions)                                  │
│  - severity (RF predictions)                                │
│  - explain (SHAP)                                           │
│  - advanced (batch, forecast, alerts, drift)                │
├─────────────────────────────────────────────────────────────┤
│  Storage:                                                   │
│  - PostgreSQL (risk_scores, severity_scores tables)         │
│  - Redis (risk score cache, TTL 300s)                       │
│  - Kafka (traffic → features → scores → severity topics)    │
├─────────────────────────────────────────────────────────────┤
│  Monitoring:                                                │
│  - Prometheus (metrics endpoint)                            │
│  - ELK (Elasticsearch + Logstash + Kibana)                  │
│  - JSON structured logging                                  │
├─────────────────────────────────────────────────────────────┤
│  Models:                                                    │
│  - RF (severity: 300 trees, XGBoost-style)                  │
│  - LSTM (risk: 2 layers, bidirectional attention)           │
│  - GAT (optional: spatial graph attention)                  │
│  - Attention-LSTM (optional: temporal attention)            │
└─────────────────────────────────────────────────────────────┘
```

---

## ℹ️ Documentation

- **FEATURES.md** – Detailed feature explanations (weather, rolling stats, temporal)
- **IMPLEMENTATION_SUMMARY.md** – Complete implementation status
- **README.md** – Project overview
- **API Docs** – http://localhost:8000/docs (auto-generated Swagger)

---

## 🚀 Next Steps

1. Start the API: `uvicorn services.api.main:app --reload`
2. Open Swagger: http://localhost:8000/docs
3. Try a prediction (POST /predict/risk)
4. Monitor metrics: http://localhost:8000/metrics
5. Review logs: http://localhost:5601 (Kibana)
6. Check drift: POST /api/v2/monitoring/drift-detection

**System is ready to use!** 🎉
