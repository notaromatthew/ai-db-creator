from app.models.schema_models import NormalizedSchema
from app.models.database import Document, get_session, init_db
from app.core.llm import _get_llm
from app.utils.exceptions import AppException
from app.utils.logger import log
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Any, Optional
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


from app.utils.json_repair import repair_and_load_json


def _normalize_schema(data: Any) -> dict:
    if isinstance(data, list):
        data = {"tables": data, "relationships": []}
    if isinstance(data, dict):
        if "schema" in data and isinstance(data["schema"], dict):
            data = data["schema"]
        elif "database" in data and isinstance(data["database"], dict):
            data = data["database"]

    raw_tables = data.get("tables", []) if isinstance(data, dict) else []
    tables = []

    for t in raw_tables:
        if not isinstance(t, dict) or "name" not in t:
            continue
        t_name = str(t.get("name", "")).strip().lower().replace(" ", "_")
        cols = []
        raw_cols = t.get("columns", [])
        has_pk = False

        for c in raw_cols:
            if not isinstance(c, dict):
                continue
            c_name = str(c.get("name") or c.get("column_name") or c.get("field") or "").strip().lower().replace(" ", "_")
            if not c_name:
                continue
            dt = str(c.get("data_type") or c.get("type") or "TEXT").upper()
            if "INT" in dt:
                dt = "INTEGER"
            elif any(k in dt for k in ("CHAR", "TEXT", "STR")):
                dt = "TEXT"
            elif any(k in dt for k in ("FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC")):
                dt = "REAL"
            elif "DATE" in dt or "TIME" in dt:
                dt = "DATE"
            elif "BOOL" in dt:
                dt = "BOOLEAN"
            else:
                dt = "TEXT"

            is_pk = bool(c.get("is_primary_key") or c.get("primary_key") or c.get("pk") or c_name == "id")
            if is_pk:
                has_pk = True

            fk_table = c.get("foreign_key_table")
            fk_col = c.get("foreign_key_column")
            is_fk = bool(c.get("is_foreign_key") or c.get("foreign_key") or c.get("fk") or fk_table)

            cols.append({
                "name": c_name,
                "data_type": dt,
                "is_primary_key": is_pk,
                "is_foreign_key": is_fk,
                "foreign_key_table": str(fk_table) if fk_table else None,
                "foreign_key_column": str(fk_col) if fk_col else ("id" if is_fk and fk_table else None),
                "is_unique": bool(c.get("is_unique")),
                "is_not_null": bool(c.get("is_not_null") or is_pk),
                "default_value": str(c.get("default_value")) if c.get("default_value") is not None else None,
                "description": str(c.get("description")) if c.get("description") else None,
            })

        if not has_pk and cols:
            cols[0]["is_primary_key"] = True

        tables.append({
            "name": t_name,
            "columns": cols,
            "description": str(t.get("description")) if t.get("description") else None,
        })

    # Cross-reference and reconcile foreign keys with actual tables & columns
    known_tables = {t["name"].lower(): t["name"] for t in tables}
    table_cols = {t["name"].lower(): {c["name"].lower(): c["name"] for c in t["columns"]} for t in tables}
    table_pks = {}
    for t in tables:
        pk = next((c["name"] for c in t["columns"] if c.get("is_primary_key")), None)
        table_pks[t["name"].lower()] = pk or (t["columns"][0]["name"] if t["columns"] else "id")

    for t in tables:
        for c in t["columns"]:
            if c.get("is_foreign_key") or c.get("foreign_key_table"):
                fk_tbl_candidate = str(c.get("foreign_key_table") or "").strip().lower().replace(" ", "_")
                if fk_tbl_candidate in known_tables:
                    target_tbl = known_tables[fk_tbl_candidate]
                    c["foreign_key_table"] = target_tbl
                    c["is_foreign_key"] = True
                    fk_col_candidate = str(c.get("foreign_key_column") or "").strip().lower().replace(" ", "_")
                    if fk_col_candidate in table_cols.get(fk_tbl_candidate, {}):
                        c["foreign_key_column"] = table_cols[fk_tbl_candidate][fk_col_candidate]
                    else:
                        c["foreign_key_column"] = table_pks.get(fk_tbl_candidate, "id")
                else:
                    c["is_foreign_key"] = False
                    c["foreign_key_table"] = None
                    c["foreign_key_column"] = None

    # Relationships
    relationships = []
    for rel in (data.get("relationships", []) if isinstance(data, dict) else []):
        if not isinstance(rel, dict) or "from_table" not in rel or "to_table" not in rel:
            continue
        t = rel.get("type", "")
        if t in ("many-to-one", "many_to_one"):
            rel_type = "one_to_many"
        elif t in ("one-to-one", "one_to_one"):
            rel_type = "one_to_one"
        elif t in ("many-to-many", "many_to_many"):
            rel_type = "many_to_many"
        else:
            rel_type = "one_to_many"

        f_tbl_raw = str(rel.get("from_table", "")).strip().lower().replace(" ", "_")
        t_tbl_raw = str(rel.get("to_table", "")).strip().lower().replace(" ", "_")
        if f_tbl_raw in known_tables and t_tbl_raw in known_tables:
            src_tbl = known_tables[f_tbl_raw]
            tgt_tbl = known_tables[t_tbl_raw]
            f_col_raw = str(rel.get("from_column", "")).strip().lower().replace(" ", "_")
            t_col_raw = str(rel.get("to_column", "")).strip().lower().replace(" ", "_")
            src_col = table_cols.get(f_tbl_raw, {}).get(f_col_raw) or table_pks.get(f_tbl_raw, "id")
            tgt_col = table_cols.get(t_tbl_raw, {}).get(t_col_raw) or table_pks.get(t_tbl_raw, "id")
            relationships.append({
                "type": rel_type,
                "from_table": src_tbl,
                "from_column": src_col,
                "to_table": tgt_tbl,
                "to_column": tgt_col,
            })

    # Infer relationships from foreign keys if none specified
    if not relationships:
        for tbl in tables:
            for col in tbl["columns"]:
                if col.get("is_foreign_key") and col.get("foreign_key_table"):
                    relationships.append({
                        "type": "one_to_many",
                        "from_table": tbl["name"],
                        "from_column": col["name"],
                        "to_table": col["foreign_key_table"],
                        "to_column": col.get("foreign_key_column", "id"),
                    })

    return {
        "tables": tables,
        "relationships": relationships,
        "description": data.get("description", "Schema generato dall'assistente AI") if isinstance(data, dict) else None,
    }


def _try_build_schema(raw: str) -> NormalizedSchema | None:
    try:
        data = repair_and_load_json(raw)
        norm = _normalize_schema(data)
        if norm.get("tables"):
            return NormalizedSchema(**norm)
    except Exception as e:
        log.warning(f"Failed to parse repaired JSON schema: {e}")
    return None


def extract_schema_from_response(response: str) -> NormalizedSchema | None:
    if not response:
        return None

    # 1. Try to repair and parse JSON directly from full response or blocks
    schema = _try_build_schema(response)
    if schema:
        return schema

    # 2. Check for SQL DDL CREATE TABLE statements
    if "CREATE TABLE" in response.upper():
        try:
            from app.core.sql_importer import extract_schema as extract_sql_schema
            sql_schema = extract_sql_schema(response, dialect="sqlite")
            if sql_schema and sql_schema.tables:
                log.info("Schema extracted from SQL DDL statements in chat response")
                return sql_schema
        except Exception as e:
            log.warning(f"SQL schema extraction failed: {e}")

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
