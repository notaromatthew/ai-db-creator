import asyncio
import sys
import types

import pytest

from app.config import settings
from app.core import llm


class _FakeVertex:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture()
def fake_vertex(monkeypatch):
    module = types.ModuleType("langchain_google_vertexai")
    module.ChatVertexAI = _FakeVertex
    monkeypatch.setitem(sys.modules, "langchain_google_vertexai", module)
    monkeypatch.setattr(settings, "llm_provider", "vertex")
    monkeypatch.setattr(settings, "vertex_project", "demo-project")
    monkeypatch.setattr(settings, "vertex_credentials_json", "")


def test_vertex_uses_low_cost_defaults(fake_vertex):
    model = llm._get_llm(temperature=0.1)
    assert model.kwargs["model_name"] == settings.vertex_model
    assert "lite" in settings.vertex_model
    assert model.kwargs["location"] == settings.vertex_location
    assert model.kwargs["max_output_tokens"] == settings.vertex_max_output_tokens
    assert model.kwargs["project"] == "demo-project"
    assert "credentials" not in model.kwargs


def test_vertex_info_label(fake_vertex):
    info = llm.get_llm_info()
    assert info["provider"] == "Google Vertex AI"
    assert info["model"] == settings.vertex_model


class _Chain:
    def __init__(self):
        self.calls = 0

    async def ainvoke(self, payload):
        self.calls += 1
        return {"n": self.calls}

    def __repr__(self):
        return "chain"


def test_cache_off_by_default_calls_model_every_time(monkeypatch):
    monkeypatch.setattr(settings, "llm_cache_enabled", False)
    llm._response_cache.clear()
    chain = _Chain()

    async def run():
        await llm._invoke(chain, {"a": 1}, cacheable=True)
        await llm._invoke(chain, {"a": 1}, cacheable=True)

    asyncio.run(run())
    assert chain.calls == 2


def test_cache_reuses_deterministic_calls_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "llm_cache_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    llm._response_cache.clear()
    chain = _Chain()

    async def run():
        first = await llm._invoke(chain, {"a": 1}, cacheable=True)
        second = await llm._invoke(chain, {"a": 1}, cacheable=True)
        assert first == second
        assert chain.calls == 1
        await llm._invoke(chain, {"a": 2}, cacheable=True)

    asyncio.run(run())
    assert chain.calls == 2


def test_sampled_calls_are_never_cached(monkeypatch):
    monkeypatch.setattr(settings, "llm_cache_enabled", True)
    llm._response_cache.clear()
    chain = _Chain()

    async def run():
        await llm._invoke(chain, {"a": 1})
        await llm._invoke(chain, {"a": 1})

    asyncio.run(run())
    assert chain.calls == 2
