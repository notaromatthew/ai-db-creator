import asyncio
from types import SimpleNamespace

from app.services import chat_service


def test_history_persists_in_database(client, project):
    pid = project["id"]
    assert chat_service.get_history(pid) == []
    chat_service.add_message(pid, "user", "ciao")
    chat_service.add_message(pid, "assistant", "salve")
    history = chat_service.get_history(pid)
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["content"] == "salve"
    chat_service.clear_history(pid)
    assert chat_service.get_history(pid) == []


def test_chat_writes_and_endpoint_returns_messages(client, project, monkeypatch):
    test_client, _ = client
    pid = project["id"]

    class FakeChain:
        async def ainvoke(self, _):
            return SimpleNamespace(content="Risposta di prova")

    class FakePrompt:
        def __or__(self, _llm):
            return FakeChain()

    monkeypatch.setattr(chat_service, "_get_llm", lambda temperature=0.3: object())
    monkeypatch.setattr(chat_service.ChatPromptTemplate, "from_messages", staticmethod(lambda *_a, **_k: FakePrompt()))

    turn = asyncio.run(chat_service.chat(pid, "voglio una biblioteca", []))
    assert turn == {"reply": "Risposta di prova", "proposal": False, "apply": False}

    response = test_client.get(f"/api/projects/{pid}/chat/history")
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [m["role"] for m in messages] == ["assistant", "user", "assistant"]
    assert messages[1]["content"] == "voglio una biblioteca"
