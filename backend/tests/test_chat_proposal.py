import asyncio
import json
from types import SimpleNamespace

import pytest

from app.models.schema_models import NormalizedSchema
from app.services import chat_service


def schema(*extra_columns):
    cols = [{"name": "id", "data_type": "INTEGER", "is_primary_key": True, "is_not_null": True}]
    cols += [{"name": c, "data_type": "TEXT"} for c in extra_columns]
    return NormalizedSchema(tables=[{"name": "clienti", "columns": cols}], relationships=[], description="d")


def fake_llm(monkeypatch, *contents):
    answers = list(contents)

    class Chain:
        async def ainvoke(self, _):
            return SimpleNamespace(content=answers.pop(0), response_metadata={})

    class Prompt:
        def __or__(self, _llm):
            return Chain()

    monkeypatch.setattr(chat_service, "_get_llm", lambda temperature=0.3: object())
    monkeypatch.setattr(chat_service.ChatPromptTemplate, "from_messages", staticmethod(lambda *_a, **_k: Prompt()))
    monkeypatch.setattr(chat_service, "APPLY_PROMPT", Prompt())


def test_parse_turn_reads_json_with_or_without_fence():
    raw = '{"reply": "Aggiungo **email**. Vuoi che le applichi?", "proposal": true, "apply": false}'
    assert chat_service._parse_turn(raw)["proposal"] is True
    assert chat_service._parse_turn("```json\n" + raw + "\n```")["reply"].startswith("Aggiungo")


def test_parse_turn_falls_back_to_plain_text_without_code():
    turn = chat_service._parse_turn("Ecco: ```json\n{\"tables\": []}\n``` fine")
    assert "tables" not in turn["reply"] and turn["proposal"] is False and turn["apply"] is False


def test_proposal_is_saved_and_blocks_nothing_until_confirmed(client, project, monkeypatch):
    pid = project["id"]
    fake_llm(monkeypatch, json.dumps({"reply": "Aggiungo l'email ai clienti. Vuoi che le applichi?", "proposal": True, "apply": False}))
    turn = asyncio.run(chat_service.chat(pid, "aggiungi email", [], existing_schema=schema()))
    assert turn["proposal"] is True and turn["apply"] is False
    assert chat_service.has_pending_proposal(pid) is True
    assert chat_service.get_history(pid)[-1]["proposal"] is True


def test_apply_only_counts_when_a_proposal_was_pending(client, project, monkeypatch):
    pid = project["id"]
    fake_llm(monkeypatch, json.dumps({"reply": "Applico.", "proposal": False, "apply": True}))
    turn = asyncio.run(chat_service.chat(pid, "sì", [], existing_schema=schema()))
    assert turn["apply"] is False  # nessuna proposta in attesa: il modello non puo' far partire una modifica

    fake_llm(monkeypatch, json.dumps({"reply": "Aggiungo l'email. Vuoi che le applichi?", "proposal": True, "apply": False}))
    asyncio.run(chat_service.chat(pid, "aggiungi email", [], existing_schema=schema()))
    fake_llm(monkeypatch, json.dumps({"reply": "Perfetto, applico.", "proposal": True, "apply": True}))
    turn = asyncio.run(chat_service.chat(pid, "sì", [], existing_schema=schema()))
    assert turn["apply"] is True and turn["proposal"] is False


def test_apply_proposal_builds_schema_and_resolves_it(client, project, monkeypatch):
    pid = project["id"]
    chat_service.add_message(pid, "assistant", "Aggiungo l'email. Vuoi che le applichi?", proposal=True)
    updated = schema("email").model_dump()
    fake_llm(monkeypatch, "```json\n" + json.dumps({"schema": updated}) + "\n```")
    result = asyncio.run(chat_service.apply_proposal(pid, schema()))
    assert [c.name for c in result.tables[0].columns] == ["id", "email"]
    assert chat_service.has_pending_proposal(pid) is False


def test_apply_proposal_fails_cleanly_on_invalid_output(client, project, monkeypatch):
    pid = project["id"]
    chat_service.add_message(pid, "assistant", "Proposta", proposal=True)
    fake_llm(monkeypatch, "non e' json")
    with pytest.raises(chat_service.AppException):
        asyncio.run(chat_service.apply_proposal(pid, schema()))
    assert chat_service.has_pending_proposal(pid) is True  # resta in attesa: l'utente puo' riprovare


def test_endpoints_apply_and_dismiss(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    # nessun schema ancora o nessuna proposta: 409
    assert c.post(f"/api/projects/{pid}/chat/apply").status_code in (409, 404)
    chat_service.add_message(pid, "assistant", "Proposta", proposal=True)
    assert c.post(f"/api/projects/{pid}/chat/dismiss").json() == {"dismissed": True}
    assert chat_service.has_pending_proposal(pid) is False
    history = c.get(f"/api/projects/{pid}/chat/history").json()["messages"]
    assert all(m["proposal"] is False for m in history)


def test_schema_with_missing_closing_braces_is_recovered():
    good = json.dumps({"schema": schema("email").model_dump()})
    truncated = good[:-1]  # il modello ha dimenticato l'ultima parentesi
    recovered = chat_service.extract_schema_from_response(truncated)
    assert recovered is not None and [c.name for c in recovered.tables[0].columns] == ["id", "email"]
    assert chat_service.extract_schema_from_response("{non json") is None
