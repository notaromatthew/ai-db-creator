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


# --- parti multimodali (testo + immagine inline) ---
import base64

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 100).decode()


def _multimodal(image=PNG, mime="image/png", role="user", extra=0):
    parts = [{"type": "text", "text": "trascrivi"}, {"type": "image", "mime_type": mime, "data": image}]
    parts += [{"type": "image", "mime_type": mime, "data": image}] * extra
    return {"messages": [{"role": role, "content": parts}], "temperature": 0.0}


REAL_CALL_VERTEX = main.call_vertex  # prima che la fixture lo sostituisca


def test_image_parts_are_forwarded_to_vertex_as_inline_data(monkeypatch):
    import google.auth
    captured = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return VERTEX

    class Creds:
        token = "t"

        def refresh(self, request):
            pass
    monkeypatch.setattr(google.auth, "default", lambda scopes=None: (Creds(), "p"))
    monkeypatch.setenv("VERTEX_PROJECT", "p")

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["body"] = json
        return Resp()
    monkeypatch.setattr(main.httpx, "post", fake_post)
    messages = [main.Message(**m) for m in _multimodal()["messages"]]
    REAL_CALL_VERTEX(messages, 0.0)
    parts = captured["body"]["contents"][0]["parts"]
    assert parts[0] == {"text": "trascrivi"}
    assert parts[1] == {"inlineData": {"mimeType": "image/png", "data": PNG}}


def test_multimodal_request_is_accepted(monkeypatch):
    _claims(monkeypatch)
    r = TestClient(main.app).post("/v1/generate", json=_multimodal(), headers=H)
    assert r.status_code == 200


def test_image_limits_and_validation(monkeypatch):
    _claims(monkeypatch)
    c = TestClient(main.app)
    monkeypatch.setenv("MAX_IMAGE_BYTES", "50")
    assert c.post("/v1/generate", json=_multimodal(), headers=H).status_code == 413
    monkeypatch.delenv("MAX_IMAGE_BYTES")
    assert c.post("/v1/generate", json=_multimodal(image="***non-base64***"), headers=H).status_code == 422
    assert c.post("/v1/generate", json=_multimodal(mime="image/svg+xml"), headers=H).status_code == 422
    assert c.post("/v1/generate", json=_multimodal(role="assistant"), headers=H).status_code == 422
    assert c.post("/v1/generate", json=_multimodal(extra=8), headers=H).status_code == 422  # 10 parti > 8
    monkeypatch.setenv("MAX_IMAGES_PER_REQUEST", "1")
    assert c.post("/v1/generate", json=_multimodal(extra=1), headers=H).status_code == 413
