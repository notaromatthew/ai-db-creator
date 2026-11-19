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


def test_message_text_supports_gemini_content_blocks():
    assert llm.message_text("SELECT 1") == "SELECT 1"
    assert llm.message_text([
        {"type": "text", "text": "INSERT INTO t "},
        {"type": "text", "text": "VALUES (1);"},
        {"type": "thinking", "thinking": "not user-facing"},
    ]) == "INSERT INTO t VALUES (1);"


def test_google_retry_limit_is_configurable(monkeypatch):
    module = types.ModuleType("langchain_google_genai")
    module.ChatGoogleGenerativeAI = _FakeVertex
    monkeypatch.setitem(sys.modules, "langchain_google_genai", module)
    monkeypatch.setattr(settings, "llm_provider", "google")
    monkeypatch.setattr(settings, "google_max_retries", 0)

    model = llm._get_llm(temperature=0.1)

    assert model.kwargs["max_retries"] == 0


def test_openrouter_disables_reasoning_and_bounds_requests(monkeypatch):
    monkeypatch.setattr(llm, "ChatOpenAI", _FakeVertex)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_model", "nvidia/nemotron-3.5-super-vl:free")
    monkeypatch.setattr(settings, "openrouter_reasoning_enabled", False)
    monkeypatch.setattr(settings, "openrouter_timeout_seconds", 90.0)
    monkeypatch.setattr(settings, "openrouter_max_retries", 0)
    monkeypatch.setattr(settings, "llm_max_tokens", 4096)

    model = llm._get_llm(temperature=0.1)

    assert model.kwargs["model"] == "nvidia/nemotron-3.5-super-vl:free"
    assert model.kwargs["max_tokens"] == 4096
    assert model.kwargs["timeout"] == 90.0
    assert model.kwargs["max_retries"] == 0
    assert model.kwargs["extra_body"] == {"reasoning": {"enabled": False}}


def test_openrouter_schema_json_mode_is_explicit_and_scoped(monkeypatch):
    monkeypatch.setattr(llm, "ChatOpenAI", _FakeVertex)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_schema_json_mode", False)

    regular = llm._get_llm(temperature=0.1)
    disabled_schema = llm._get_llm(temperature=0.1, structured_json=True)
    monkeypatch.setattr(settings, "openrouter_schema_json_mode", True)
    schema = llm._get_llm(temperature=0.1, structured_json=True)

    assert "model_kwargs" not in regular.kwargs
    assert "model_kwargs" not in disabled_schema.kwargs
    response_format = schema.kwargs["model_kwargs"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "normalized_schema"
    assert response_format["json_schema"]["strict"] is False
    assert response_format["json_schema"]["schema"] == llm.NormalizedSchema.model_json_schema()
    assert llm.get_llm_info()["schema_output_contract"] == "schema-json-v2"


def test_schema_repair_extracts_and_validates_one_json_object():
    payload = {
        "tables": [{
            "name": "patients",
            "columns": [{"name": "patient_id", "data_type": "INTEGER"}],
        }],
        "relationships": [],
    }
    raw = types.SimpleNamespace(content=f"prefix {__import__('json').dumps(payload)} suffix")

    schema, repair = llm._repair_schema_output(raw)

    assert schema.tables[0].name == "patients"
    assert repair == "deterministic_json_extract"


def test_schema_repair_classifies_truncated_json():
    raw = types.SimpleNamespace(content='{"tables": [')

    with pytest.raises(ValueError, match="truncated_json"):
        llm._repair_schema_output(raw)
