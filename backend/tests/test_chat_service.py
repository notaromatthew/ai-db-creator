import asyncio

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.models.schema_models import NormalizedSchema
from app.services import chat_service


def test_extraction_prompt_only_requires_history():
    assert chat_service.EXTRACTION_PROMPT.input_variables == ["history"]
    messages = chat_service.EXTRACTION_PROMPT.format_messages(history="user: crea un catalogo")
    assert '"schema"' in messages[0].content
    assert '"name"' in messages[0].content


def test_schema_extraction_fallback_returns_valid_schema(monkeypatch):
    payload = (
        '{"schema":{"tables":[{"name":"prodotti","columns":['
        '{"name":"id","data_type":"INTEGER","is_primary_key":true}]}],'
        '"relationships":[],"description":"Catalogo"}}'
    )
    fake_llm = RunnableLambda(lambda _: AIMessage(content=payload))
    monkeypatch.setattr(chat_service, "_get_llm", lambda temperature: fake_llm)
    monkeypatch.setattr(
        chat_service,
        "get_history",
        lambda _project_id: [{"role": "user", "content": "crea un catalogo"}],
    )

    schema = asyncio.run(
        chat_service.extract_schema_with_fallback("project-1", "Nessun JSON nella risposta")
    )

    assert isinstance(schema, NormalizedSchema)
    assert schema.tables[0].name == "prodotti"
