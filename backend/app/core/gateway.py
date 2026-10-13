"""Client del gateway LLM su Cloud Run.

Se LLM_GATEWAY_URL e' impostata, il provider vertex chiama il gateway con un ID token
(google-auth) invece di Vertex direttamente. Senza la variabile resta la chiamata diretta
(test locali). La variabile e' letta qui con os.getenv: config.py non cambia.
"""
import json
import os
import time
from typing import Any, List, Optional

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def gateway_url() -> str:
    return os.getenv("LLM_GATEWAY_URL", "").strip().rstrip("/")


def gateway_enabled() -> bool:
    return bool(gateway_url())


_token_cache: dict = {"token": None, "exp": 0.0}


def get_id_token(audience: str) -> str:
    """ID token per l'audience del gateway; riusato fino a 5 minuti dalla scadenza."""
    if _token_cache["token"] and _token_cache["exp"] - 300 > time.time():
        return _token_cache["token"]
    from google.auth.transport.requests import Request
    raw = os.getenv("GATEWAY_CALLER_CREDENTIALS_JSON", "").strip() or os.getenv("VERTEX_CREDENTIALS_JSON", "").strip()
    if raw:
        from google.oauth2 import service_account
        creds = service_account.IDTokenCredentials.from_service_account_info(
            json.loads(raw), target_audience=audience)
        creds.refresh(Request())
        token = creds.token
    else:
        from google.oauth2 import id_token
        token = id_token.fetch_id_token(Request(), audience)
    _token_cache.update(token=token, exp=time.time() + 3300)
    return token


_ROLES = {"system": "system", "human": "user", "ai": "assistant"}


MAX_PARTS_PER_MESSAGE = 8
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # dimensione decodificata di una singola immagine
IMAGE_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")


def _content_payload(content):
    """Testo semplice oppure elenco di parti {type: text|image}: le immagini inline arrivano come base64."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)
    if len(content) > MAX_PARTS_PER_MESSAGE:
        raise ValueError(f"Troppe parti nel messaggio (massimo {MAX_PARTS_PER_MESSAGE}).")
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append({"type": "text", "text": item})
        elif isinstance(item, dict) and item.get("type") == "text":
            parts.append({"type": "text", "text": str(item.get("text", ""))})
        elif isinstance(item, dict) and item.get("type") == "image_url":
            url = item.get("image_url")
            url = url.get("url") if isinstance(url, dict) else url
            head, _, data = str(url or "").partition(",")
            if not (head.startswith("data:") and head.endswith(";base64")):
                raise ValueError("Sono ammesse solo immagini inline in base64.")
            mime = head[5:-7]
            if mime not in IMAGE_MIME_TYPES:
                raise ValueError("Formato immagine non ammesso.")
            if len(data) * 3 // 4 > MAX_IMAGE_BYTES:
                raise ValueError("Immagine troppo grande.")
            parts.append({"type": "image", "mime_type": mime, "data": data})
        else:
            raise ValueError("Parte del messaggio non supportata.")
    return parts


def _payload(messages: List[BaseMessage], temperature: float) -> dict:
    return {
        "messages": [{"role": _ROLES.get(m.type, "user"), "content": _content_payload(m.content)} for m in messages],
        "temperature": temperature,
    }


def _to_result(data: dict) -> ChatResult:
    tin, tout = int(data.get("input_tokens", 0)), int(data.get("output_tokens", 0))
    msg = AIMessage(content=data.get("text", ""),
                    usage_metadata={"input_tokens": tin, "output_tokens": tout, "total_tokens": tin + tout})
    return ChatResult(generations=[ChatGeneration(message=msg)])


class GatewayChatModel(BaseChatModel):
    temperature: float = 0.1
    timeout: float = 120.0

    @property
    def _llm_type(self) -> str:
        return "aidb-gateway"

    def _call_args(self, messages):
        url = gateway_url()
        headers = {"Authorization": f"Bearer {get_id_token(url)}"}
        return f"{url}/v1/generate", _payload(messages, self.temperature), headers

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        url, body, headers = self._call_args(messages)
        resp = httpx.post(url, json=body, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return _to_result(resp.json())

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                         run_manager: Optional[AsyncCallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        url, body, headers = self._call_args(messages)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return _to_result(resp.json())
