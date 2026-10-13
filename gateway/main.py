"""Gateway sottile e senza stato davanti a Vertex AI (Cloud Run).

- Autenticazione: ID token OIDC dell'identita' chiamante, audience verificata.
- Modello e token massimi sono fissati QUI (variabili d'ambiente del servizio), non dal chiamante.
- Registro dei token su stdout (JSON), interruttore AI e tetto giornaliero di richieste.
Il contatore giornaliero e' in memoria: per questo Terraform imposta max istanze = 1.
"""
import base64
import binascii
import datetime as dt
import json
import logging
import os
import threading

import httpx
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(level=logging.INFO, format="%(message)s")
_log = logging.getLogger("gateway")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def ai_enabled() -> bool:
    return _env("AI_ENABLED", "true").lower() in ("1", "true", "yes", "on")


def allowed_callers() -> set[str]:
    return {c.strip().lower() for c in _env("ALLOWED_CALLERS").split(",") if c.strip()}


def log_event(**fields) -> None:
    _log.info(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(), **fields}))


class _DailyCounter:
    def __init__(self):
        self._lock = threading.Lock()
        self._day = None
        self._count = 0

    def hit(self, cap: int) -> bool:
        """True se la richiesta rientra nel tetto del giorno (UTC); la conta."""
        today = dt.datetime.now(dt.timezone.utc).date()
        with self._lock:
            if self._day != today:
                self._day, self._count = today, 0
            if cap > 0 and self._count >= cap:
                return False
            self._count += 1
            return True

    def reset(self):
        with self._lock:
            self._day, self._count = None, 0


counter = _DailyCounter()


def verify_caller(authorization: str = Header(default="")) -> str:
    """Verifica l'ID token Google: firma, scadenza, audience, e-mail ammessa."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "token mancante")
    token = authorization[7:].strip()
    audience = _env("GATEWAY_AUDIENCE")
    if not audience:
        raise HTTPException(500, "audience non configurata")
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token
        claims = id_token.verify_oauth2_token(token, g_requests.Request(), audience=audience)
    except Exception:
        raise HTTPException(401, "token non valido")
    email = str(claims.get("email", "")).lower()
    if not claims.get("email_verified", False) or email not in allowed_callers():
        raise HTTPException(403, "chiamante non ammesso")
    return email


MAX_PARTS_PER_MESSAGE = 8
IMAGE_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class ImagePart(BaseModel):
    type: Literal["image"]
    mime_type: str
    data: str  # base64

    @field_validator("mime_type")
    @classmethod
    def _mime(cls, value):
        if value not in IMAGE_MIME_TYPES:
            raise ValueError("formato immagine non ammesso")
        return value


class Message(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str | list[Annotated[TextPart | ImagePart, Field(discriminator="type")]]

    @field_validator("content")
    @classmethod
    def _limit_parts(cls, value):
        if isinstance(value, list) and not 1 <= len(value) <= MAX_PARTS_PER_MESSAGE:
            raise ValueError("numero di parti non ammesso")
        return value

    def parts(self) -> list:
        return [TextPart(type="text", text=self.content)] if isinstance(self.content, str) else self.content

    def text(self) -> str:
        return "".join(p.text for p in self.parts() if isinstance(p, TextPart))


def validate_images(messages: list["Message"]) -> None:
    """Immagini solo nei messaggi dell'utente, base64 valido, dimensione e numero entro i limiti."""
    max_bytes = int(_env("MAX_IMAGE_BYTES", str(4 * 1024 * 1024)))
    max_images = int(_env("MAX_IMAGES_PER_REQUEST", "8"))
    total = 0
    for message in messages:
        for part in message.parts():
            if not isinstance(part, ImagePart):
                continue
            if message.role != "user":
                raise HTTPException(422, "immagini ammesse solo nei messaggi utente")
            total += 1
            try:
                raw = base64.b64decode(part.data, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(422, "immagine non valida")
            if not raw or len(raw) > max_bytes:
                raise HTTPException(413, "immagine troppo grande")
    if total > max_images:
        raise HTTPException(413, "troppe immagini nella richiesta")


class GenerateRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=64)
    temperature: float = 0.1


class GenerateResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


def _vertex_parts(message: Message) -> list[dict]:
    return [{"text": p.text} if isinstance(p, TextPart) else {"inlineData": {"mimeType": p.mime_type, "data": p.data}}
            for p in message.parts()]


def call_vertex(messages: list[Message], temperature: float) -> dict:
    """Chiamata REST a Vertex con le credenziali del service account del gateway."""
    import google.auth
    from google.auth.transport.requests import Request

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    project, location, model = _env("VERTEX_PROJECT"), _env("VERTEX_LOCATION", "europe-west4"), _env("VERTEX_MODEL", "gemini-2.5-flash-lite")
    url = (f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
           f"/locations/{location}/publishers/google/models/{model}:generateContent")
    system = "\n\n".join(m.text() for m in messages if m.role == "system")
    contents = [{"role": "model" if m.role == "assistant" else "user", "parts": _vertex_parts(m)}
                for m in messages if m.role != "system"]
    body = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": int(_env("MAX_OUTPUT_TOKENS", "2048")),
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    resp = httpx.post(url, json=body, headers={"Authorization": f"Bearer {creds.token}"}, timeout=120)
    resp.raise_for_status()
    return resp.json()


app = FastAPI(title="AI-DB-Creator LLM gateway", docs_url=None, redoc_url=None)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "ai_enabled": ai_enabled()}


@app.post("/v1/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, caller: str = Depends(verify_caller)):
    if not ai_enabled():
        log_event(event="blocked", reason="ai_disabled", caller=caller)
        raise HTTPException(503, "chiamate AI disattivate")
    if sum(len(m.text()) for m in req.messages) > int(_env("MAX_INPUT_CHARS", "200000")):
        raise HTTPException(413, "richiesta troppo lunga")
    validate_images(req.messages)
    if not counter.hit(int(_env("DAILY_REQUEST_CAP", "500"))):
        log_event(event="blocked", reason="daily_cap", caller=caller)
        raise HTTPException(429, "tetto giornaliero raggiunto")
    temperature = min(max(req.temperature, 0.0), 1.0)
    try:
        data = call_vertex(req.messages, temperature)
        cand = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        usage = data.get("usageMetadata", {})
    except HTTPException:
        raise
    except Exception as exc:
        log_event(event="upstream_error", caller=caller, error=type(exc).__name__)
        raise HTTPException(502, "errore del modello")
    tin, tout = int(usage.get("promptTokenCount", 0)), int(usage.get("candidatesTokenCount", 0))
    model = _env("VERTEX_MODEL", "gemini-2.5-flash-lite")
    log_event(event="generate", caller=caller, model=model, input_tokens=tin, output_tokens=tout)
    return GenerateResponse(text=text, model=model, input_tokens=tin, output_tokens=tout)
