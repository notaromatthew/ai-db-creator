import asyncio

import pytest

from app.core import llm
from app.utils.exceptions import LLMException


class RawMessage:
    def __init__(self, content):
        self.content = content
        self.response_metadata = {"finish_reason": "stop"}
        self.usage_metadata = {"output_tokens": 123}


VALID_SCHEMA = {
    "tables": [{
        "name": "books",
        "columns": [{"name": "book_id", "data_type": "INTEGER", "is_primary_key": True}],
    }],
    "relationships": [],
}


class RejectingParser:
    @staticmethod
    def get_format_instructions():
        return "json schema instructions"

    @staticmethod
    def invoke(_raw):
        raise ValueError("parse")


def test_generate_schema_repairs_one_embedded_json_object(monkeypatch):
    raw = RawMessage("Result:\n```json\n" + __import__("json").dumps(VALID_SCHEMA) + "\n```")
    monkeypatch.setattr(llm, "_get_llm", lambda **_kwargs: object())
    monkeypatch.setattr(llm.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm.settings, "openrouter_schema_json_mode", True)

    async def fake_invoke(*_args, **_kwargs):
        return raw

    monkeypatch.setattr(llm, "_invoke", fake_invoke)
    monkeypatch.setattr(llm, "schema_parser", RejectingParser())
    messages = []
    monkeypatch.setattr(llm.log, "warning", messages.append)

    schema = asyncio.run(llm.generate_schema("safe prompt"))

    assert schema.tables[0].name == "books"
    assert "parse_category=standard_parser_failed" in messages[0]
    assert "repair=deterministic_json_extract" in messages[0]
    assert "finish_reason=stop" in messages[0]
    assert "output_tokens=123" in messages[0]
    assert "safe prompt" not in messages[0]


@pytest.mark.parametrize("content, category", [
    ('{"tables": [', "truncated_json"),
    ('not json SECRET_RAW_VALUE', "json_object_missing"),
    ('{"tables": "wrong", "relationships": []}', "schema_validation"),
])
def test_generate_schema_rejects_unrepairable_output_without_logging_raw(
    monkeypatch, content, category
):
    raw = RawMessage(content)
    monkeypatch.setattr(llm, "_get_llm", lambda **_kwargs: object())
    monkeypatch.setattr(llm.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm.settings, "openrouter_schema_json_mode", True)

    async def fake_invoke(*_args, **_kwargs):
        return raw

    monkeypatch.setattr(llm, "_invoke", fake_invoke)
    monkeypatch.setattr(llm, "schema_parser", RejectingParser())
    errors = []
    monkeypatch.setattr(llm.log, "error", errors.append)

    with pytest.raises(LLMException):
        asyncio.run(llm.generate_schema("PROMPT_SECRET"))

    assert any(f"parse_category={category}" in message for message in errors)
    assert all("SECRET_RAW_VALUE" not in message for message in errors)
    assert all("PROMPT_SECRET" not in message for message in errors)


def test_legacy_contract_does_not_attempt_repair(monkeypatch):
    raw = RawMessage(__import__("json").dumps(VALID_SCHEMA))
    monkeypatch.setattr(llm, "_get_llm", lambda **_kwargs: object())
    monkeypatch.setattr(llm.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm.settings, "openrouter_schema_json_mode", False)

    async def fake_invoke(*_args, **_kwargs):
        return raw

    monkeypatch.setattr(llm, "_invoke", fake_invoke)
    monkeypatch.setattr(llm, "schema_parser", RejectingParser())
    monkeypatch.setattr(
        llm, "_repair_schema_output",
        lambda _raw: (_ for _ in ()).throw(AssertionError("repair must remain disabled")),
    )

    with pytest.raises(LLMException):
        asyncio.run(llm.generate_schema("legacy prompt"))
