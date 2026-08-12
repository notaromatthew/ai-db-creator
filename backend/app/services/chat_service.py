from app.models.schema_models import NormalizedSchema
from app.models.database import Document, get_session, init_db
from app.core.llm import _get_llm
from app.utils.exceptions import AppException
from app.utils.logger import log
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Optional
import json
import re

_conversations: dict[str, list] = {}

SYSTEM_PROMPT = """Sei un assistente esperto di progettazione di database. Il tuo scopo è aiutare l'utente a progettare uno schema di database normalizzato tramite conversazione in italiano.

Linee guida:
1. Inizia chiedendo all'utente che tipo di dati deve memorizzare. Fai domande di chiarimento se necessario.
2. Suggerisci tabelle, colonne, relazioni e tipi di dati in base alla descrizione e ai documenti caricati.
3. Proponi miglioramenti: tabelle aggiuntive, migliore normalizzazione, relazioni mancanti.
4. Quando hai abbastanza informazioni, proponi lo schema spiegandolo in italiano semplice, senza usare termini tecnici.
5. Metti il JSON dello schema in un blocco ```json in modo che il sistema possa elaborarlo.

Struttura JSON richiesta:

```json
{{"schema": {{"tables": [...], "relationships": [...], "description": "..."}}}}
```

Ogni tabella:
{{"name": "nome_tabelle_plurale", "description": "cosa contiene", "columns": [{{"name": "nome_colonna", "data_type": "INTEGER|TEXT|REAL|DATE|BOOLEAN", "is_primary_key": true|false, "is_foreign_key": true|false, "foreign_key_table": "..." se FK, "foreign_key_column": "..." se FK, "is_unique": true|false, "is_not_null": true|false, "default_value": "...", "description": "..."}}]}}

REGOLE IMPORTANTI:
- Non usare MAI comandi SQL. Usa solo il formato JSON qui sopra per proporre lo schema.
- Spiega lo schema in italiano semplice, come se parlassi a una persona che non sa cosa sia un database.
- Descrivi ogni tabella in modo chiaro: "questa tabella conterrà i clienti con nome e cognome", ecc.
- Il JSON deve essere dentro un blocco ```json (verrà nascosto all'utente dal sistema).
- Chiedi sempre all'utente se vuole accettare lo schema o apportare modifiche."""


def get_history(project_id: str) -> list:
    return _conversations.get(project_id, [])


def add_message(project_id: str, role: str, content: str, extra: Optional[dict] = None):
    if project_id not in _conversations:
        _conversations[project_id] = []
    msg = {"role": role, "content": content}
    if extra:
        msg["extra"] = extra
    _conversations[project_id].append(msg)


def clear_history(project_id: str):
    _conversations.pop(project_id, None)


def build_doc_context(project_id: str, document_ids: list[str]) -> str:
    if not document_ids:
        return ""
    engine = init_db()
    session = get_session(engine)
    parts = []
    for doc_id in document_ids:
        doc = session.query(Document).filter(Document.id == doc_id, Document.project_id == project_id).first()
        if not doc:
            session.close()
            raise AppException(detail="Document not found", status_code=404)
        if doc and doc.content_summary:
            parts.append(f"--- {doc.filename} ---\n{doc.content_summary}")
    session.close()
    return "\n\n".join(parts)


async def chat(project_id: str, message: str, document_ids: list[str], existing_schema: Optional[NormalizedSchema] = None) -> str:
    doc_context = build_doc_context(project_id, document_ids)
    history = get_history(project_id)

    if not history:
        intro = "I'll help you design a database schema. Describe what data you need to store"
        if doc_context:
            intro += f", considering the uploaded documents"
        intro += "."
        add_message(project_id, "assistant", intro)
        history = get_history(project_id)

    add_message(project_id, "user", message)
    history = get_history(project_id)

    try:
        llm = _get_llm(temperature=0.3)

        schema_context = ""
        if existing_schema:
            schema_context = f"\nCurrent schema:\n{json.dumps(existing_schema.model_dump(), indent=2)}\n\nIf the user requests changes, modify the existing schema instead of creating a new one."

        msg_history = []
        for h in history:
            if h["role"] == "user":
                msg_history.append(HumanMessage(content=h["content"]))
            else:
                msg_history.append(AIMessage(content=h["content"]))

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + "\n\nUploaded documents context:\n{doc_context}\n{schema_context}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        chain = prompt | llm
        result = await chain.ainvoke({
            "doc_context": doc_context or "No documents uploaded.",
            "schema_context": schema_context,
            "history": msg_history[:-1],
            "input": message,
        })

        response = result.content.strip()
    except Exception as e:
        log.error(f"Chat LLM call failed ({type(e).__name__})")
        raise AppException(detail="Chat generation failed", status_code=502) from e

    add_message(project_id, "assistant", response)
    return response


def _truncate_json(raw: str) -> str:
    """Cut trailing text that may follow the closing brace of the JSON object."""
    idx = raw.rfind('}')
    if idx != -1:
        return raw[:idx + 1]
    return raw.strip()


def _normalize_schema(data: dict) -> dict:
    if "schema" in data:
        data = data["schema"]
    for rel in data.get("relationships", []):
        t = rel.get("type", "")
        if t in ("many-to-one", "many_to_one"):
            rel["type"] = "one_to_many"
        elif t in ("one-to-one",):
            rel["type"] = "one_to_one"
        elif t in ("many-to-many",):
            rel["type"] = "many_to_many"
        elif not t:
            rel["type"] = "one_to_many"
    return data


def _try_build_schema(raw: str) -> NormalizedSchema | None:
    try:
        data = json.loads(raw)
        data = _normalize_schema(data)
        return NormalizedSchema(**data)
    except Exception as e:
        log.warning(f"Failed to parse JSON schema: {e}")
        return None


def extract_schema_from_response(response: str) -> NormalizedSchema | None:
    import re
    match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
    if match:
        raw = _truncate_json(match.group(1).strip())
        schema = _try_build_schema(raw)
        if schema:
            return schema
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        raw = _truncate_json(match.group(0))
        schema = _try_build_schema(raw)
        if schema:
            return schema
    return None


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a database schema designer. Based on the conversation so far, output ONLY the complete JSON schema object for the database being designed. "
               "Do NOT add explanations, comments, or markdown. Output only the raw JSON.\n"
               "Structure: {{\"schema\": {{\"tables\": [...], \"relationships\": [...], \"description\": \"...\"}}}}\n"
               "Each table: {{\"name\": \"nome_tabelle_plurale\", \"description\": \"cosa contiene\", \"columns\": [{{\"name\": \"nome_colonna\", \"data_type\": \"INTEGER|TEXT|REAL|DATE|BOOLEAN\", \"is_primary_key\": true|false, \"is_foreign_key\": true|false, \"foreign_key_table\": \"...\" se FK, \"foreign_key_column\": \"...\" se FK, \"is_unique\": false, \"is_not_null\": false, \"description\": \"...\"}}]}}\n"
               "Each relationship MUST include the \"type\" field: one_to_many, many_to_many, or one_to_one."),
    ("system", "Conversation so far:\n{history}"),
    ("user", "Output the complete JSON schema for the database described above."),
])


async def extract_schema_with_fallback(project_id: str, response: str, existing_schema: Optional[NormalizedSchema] = None) -> NormalizedSchema | None:
    """Try to extract a schema from the chat response; if not possible, ask the LLM for it explicitly."""
    schema = extract_schema_from_response(response)
    if schema:
        return schema

    history = get_history(project_id)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-20:])
    if existing_schema:
        history_text += f"\n\nCurrent schema:\n{json.dumps(existing_schema.model_dump(), indent=2)}"

    try:
        llm = _get_llm(temperature=0.1)
        chain = EXTRACTION_PROMPT | llm
        result = await chain.ainvoke({"history": history_text or "No previous conversation."})
        extracted = extract_schema_from_response(result.content)
        if extracted:
            log.info("Schema extracted via LLM fallback")
        return extracted
    except Exception as e:
        log.error(f"Schema extraction fallback failed ({type(e).__name__})")
        return None
