import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402

BODY = {"messages": [{"role": "user", "content": "ciao"}], "temperature": 0.2}
VERTEX = {"candidates": [{"content": {"parts": [{"text": "risposta"}]}}],
          "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 7}}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GATEWAY_AUDIENCE", "https://gw.example")
    monkeypatch.setenv("ALLOWED_CALLERS", "caller@p.iam.gserviceaccount.com")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("DAILY_REQUEST_CAP", "2")
    main.counter.reset()
    monkeypatch.setattr(main, "call_vertex", lambda m, t: VERTEX)


def _claims(monkeypatch, claims=None, fail=False):
    from google.oauth2 import id_token

    def fake(token, request, audience=None):
        assert audience == "https://gw.example"
        if fail:
            raise ValueError("bad")
        return claims or {"email": "caller@p.iam.gserviceaccount.com", "email_verified": True}
    monkeypatch.setattr(id_token, "verify_oauth2_token", fake)


H = {"Authorization": "Bearer tok"}


def test_ok_and_usage(monkeypatch):
    _claims(monkeypatch)
    r = TestClient(main.app).post("/v1/generate", json=BODY, headers=H)
    assert r.status_code == 200
    assert r.json()["text"] == "risposta" and r.json()["output_tokens"] == 7


def test_no_token():
    assert TestClient(main.app).post("/v1/generate", json=BODY).status_code == 401


def test_bad_token(monkeypatch):
    _claims(monkeypatch, fail=True)
    assert TestClient(main.app).post("/v1/generate", json=BODY, headers=H).status_code == 401


def test_caller_not_allowed(monkeypatch):
    _claims(monkeypatch, {"email": "evil@x.com", "email_verified": True})
    assert TestClient(main.app).post("/v1/generate", json=BODY, headers=H).status_code == 403


def test_kill_switch(monkeypatch):
    _claims(monkeypatch)
    monkeypatch.setenv("AI_ENABLED", "false")
    assert TestClient(main.app).post("/v1/generate", json=BODY, headers=H).status_code == 503


def test_daily_cap(monkeypatch):
    _claims(monkeypatch)
    c = TestClient(main.app)
    codes = [c.post("/v1/generate", json=BODY, headers=H).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_model_not_selectable_by_caller(monkeypatch):
    _claims(monkeypatch)
    seen = {}
    monkeypatch.setattr(main, "call_vertex", lambda m, t: seen.setdefault("t", t) and VERTEX)
    body = {**BODY, "model": "gemini-pro", "max_tokens": 999999, "temperature": 5}
    assert TestClient(main.app).post("/v1/generate", json=body, headers=H).status_code == 200
    assert seen["t"] == 1.0


def test_healthz():
    assert TestClient(main.app).get("/healthz").status_code == 200
