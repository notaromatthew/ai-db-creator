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
    assert isinstance(llm._get_llm(0.2), gateway.GatewayChatModel)


def test_multimodal_parts_are_sent_as_text_and_inline_image(monkeypatch):
    import base64
    seen = {}

    def handler(req: httpx.Request):
        seen["body"] = __import__("json").loads(req.read().decode())
        return httpx.Response(200, json={"text": "ok", "model": "m", "input_tokens": 1, "output_tokens": 1})

    _mock(monkeypatch, handler)
    png = base64.b64encode(b"\x89PNG" + b"0" * 50).decode()
    message = HumanMessage(content=[
        {"type": "text", "text": "trascrivi"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + png}},
    ])
    assert gateway.GatewayChatModel().invoke([message]).content == "ok"
    assert seen["body"]["messages"][0]["content"] == [
        {"type": "text", "text": "trascrivi"}, {"type": "image", "mime_type": "image/png", "data": png}]


def test_multimodal_limits_are_enforced_before_sending(monkeypatch):
    import base64
    big = base64.b64encode(b"0" * (gateway.MAX_IMAGE_BYTES + 10)).decode()
    url = lambda data, mime="image/png": {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}
    with pytest.raises(ValueError):
        gateway._content_payload([url(big)])
    with pytest.raises(ValueError):
        gateway._content_payload([url("QQ==", "image/svg+xml")])
    with pytest.raises(ValueError):
        gateway._content_payload([url("QQ==")] * (gateway.MAX_PARTS_PER_MESSAGE + 1))
    with pytest.raises(ValueError):
        gateway._content_payload([{"type": "image_url", "image_url": {"url": "https://x/y.png"}}])
