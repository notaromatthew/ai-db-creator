import asyncio
import httpx
import pytest

from app.core import gateway
from langchain_core.messages import HumanMessage, SystemMessage

URL = "https://gw.example"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", URL + "/")
    monkeypatch.setattr(gateway, "get_id_token", lambda aud: "TOKEN")


def _mock(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw))
    real_post = httpx.post
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Client(transport=transport).post(url, **{k: v for k, v in kw.items() if k != "timeout"}))
    return real_post


def test_enabled_flag(monkeypatch):
    assert gateway.gateway_enabled()
    monkeypatch.delenv("LLM_GATEWAY_URL")
    assert not gateway.gateway_enabled()


def test_sync_call_with_token(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        seen["auth"] = req.headers["authorization"]
        seen["url"] = str(req.url)
        seen["body"] = req.read().decode()
        return httpx.Response(200, json={"text": "ok", "model": "m", "input_tokens": 3, "output_tokens": 4})

    _mock(monkeypatch, handler)
    out = gateway.GatewayChatModel(temperature=0.3).invoke([SystemMessage(content="s"), HumanMessage(content="u")])
    assert out.content == "ok"
    assert out.usage_metadata["output_tokens"] == 4
    assert seen["auth"] == "Bearer TOKEN" and seen["url"] == URL + "/v1/generate"
    assert '"role": "system"' in seen["body"] or '"role":"system"' in seen["body"]


def test_async_call_and_error(monkeypatch):
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(200, json={"text": "a", "input_tokens": 1, "output_tokens": 1})
        return httpx.Response(429, json={"detail": "tetto"})

    _mock(monkeypatch, handler)
    llm = gateway.GatewayChatModel()
    assert asyncio.run(llm.ainvoke("ciao")).content == "a"
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(llm.ainvoke("ciao"))


def test_llm_uses_gateway_for_vertex(monkeypatch):
    from app.core import llm
    monkeypatch.setattr(llm.settings, "llm_provider", "vertex")
    monkeypatch.setattr(llm.settings, "use_ollama", False)
    assert isinstance(llm._get_llm(0.2), gateway.GatewayChatModel)
