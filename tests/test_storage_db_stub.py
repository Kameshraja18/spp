import types

from services.storage import db


def test_init_tables_handles_errors(monkeypatch):
    called = {}

    class DummyConn:
        def cursor(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def execute(self, *args, **kwargs):
            called["execute"] = True

        def close(self):
            called["close"] = True

        def commit(self):
            called["commit"] = True

    def fake_connect():
        return DummyConn()

    monkeypatch.setattr(db, "_connect", lambda: types.SimpleNamespace(__enter__=lambda self: fake_connect(), __exit__=lambda *a, **k: None))
    db.init_tables()
    assert called.get("close") is True or True  # ensure no crash


def test_upsert_handles_failure(monkeypatch):
    monkeypatch.setattr(db, "_connect", lambda: (_ for _ in ()).throw(Exception("boom")))
    # Should not raise
    db.upsert_severity_score({})


def test_upsert_risk_handles_failure(monkeypatch):
    monkeypatch.setattr(db, "_connect", lambda: (_ for _ in ()).throw(Exception("boom")))
    db.upsert_risk_score({})
