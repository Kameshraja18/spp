from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

import psycopg2

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/accidents")


@contextmanager
def _connect():
    conn = psycopg2.connect(POSTGRES_DSN)
    try:
        yield conn
    finally:
        conn.close()


def upsert_severity_score(payload: Dict[str, Any]) -> None:
    """Persist latest severity score keyed by road_segment_id."""
    sql = (
        "INSERT INTO severity_scores (road_segment_id, severity_class, severity_label, no_injury, minor, serious, fatal) "
        "VALUES (%(road_segment_id)s, %(severity_class)s, %(severity_label)s, %(no_injury)s, %(minor)s, %(serious)s, %(fatal)s) "
        "ON CONFLICT (road_segment_id) DO UPDATE SET "
        "severity_class = EXCLUDED.severity_class, "
        "severity_label = EXCLUDED.severity_label, "
        "no_injury = EXCLUDED.no_injury, "
        "minor = EXCLUDED.minor, "
        "serious = EXCLUDED.serious, "
        "fatal = EXCLUDED.fatal"
    )
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)
            conn.commit()
    except Exception:
        # DB errors should not break the pipeline path.
        return


def upsert_risk_score(payload: Dict[str, Any]) -> None:
    sql = (
        "INSERT INTO risk_scores (road_segment_id, risk_score, risk_label, prediction_horizon_min) "
        "VALUES (%(road_segment_id)s, %(risk_score)s, %(risk_label)s, %(prediction_horizon_min)s) "
        "ON CONFLICT (road_segment_id) DO UPDATE SET "
        "risk_score = EXCLUDED.risk_score, "
        "risk_label = EXCLUDED.risk_label, "
        "prediction_horizon_min = EXCLUDED.prediction_horizon_min"
    )
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, payload)
            conn.commit()
    except Exception:
        return


def init_tables() -> None:
    sql_severity = (
        "CREATE TABLE IF NOT EXISTS severity_scores ("
        "road_segment_id TEXT PRIMARY KEY, "
        "severity_class INT, "
        "severity_label TEXT, "
        "no_injury DOUBLE PRECISION, "
        "minor DOUBLE PRECISION, "
        "serious DOUBLE PRECISION, "
        "fatal DOUBLE PRECISION"
        ")"
    )
    sql_risk = (
        "CREATE TABLE IF NOT EXISTS risk_scores ("
        "road_segment_id TEXT PRIMARY KEY, "
        "risk_score DOUBLE PRECISION, "
        "risk_label TEXT, "
        "prediction_horizon_min INT"
        ")"
    )
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_severity)
                cur.execute(sql_risk)
            conn.commit()
    except Exception:
        return
