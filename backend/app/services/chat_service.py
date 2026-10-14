from app.models.schema_models import NormalizedSchema
from app.models.database import ChatMessage, Document, get_session, init_db
from app.core.llm import _get_llm
from app.utils.exceptions import AppException
from app.utils.logger import log
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Optional
import json
import re

SYSTEM_PROMPT = """Sei un assistente che aiuta una persona a rifinire lo schema di un database. Parli in italiano semplice, senza termini tecnici, come a chi non sa cosa sia un database.

Come lavori:
- Capisci cosa vuole cambiare e proponi poche modifiche concrete, in una breve lista (al massimo 5 punti).
- Non scrivere mai JSON, SQL, codice o l'elenco completo di tabelle e colonne: lo schema vero lo aggiorna il sistema solo dopo la conferma dell'utente.
- Non dire mai che hai gia' applicato o salvato una modifica: tu proponi, il sistema applica quando l'utente conferma.
- Risposte brevi: al massimo 90 parole. Puoi usare **grassetto** e liste con il trattino.
- Se la richiesta non e' chiara, fai una sola domanda breve.

Rispondi SEMPRE e SOLO con un oggetto JSON di questa forma, senza altro testo:
{{"reply": "<testo per l'utente>", "proposal": true|false, "apply": true|false}}

- "proposal" e' true solo se nel testo proponi modifiche concrete allo schema e aspetti la conferma; in quel caso chiudi con la domanda "Vuoi che le applichi?".
- "apply" e' true solo se l'ultimo messaggio dell'utente accetta chiaramente la proposta in attesa (indicata sotto). In quel caso "reply" e' una frase breve tipo "Perfetto, applico le modifiche." e "proposal" e' false.
- Se non c'e' nessuna proposta in attesa, "apply" e' sempre false."""


def get_history(project_id: str) -> list:
    """Messaggi del progetto in ordine cronologico, letti dal database."""
    session = get_session(init_db())
    try:
        rows = (session.query(ChatMessage).filter(ChatMessage.project_id == project_id)
                .order_by(ChatMessage.created_at).all())
        return [{"id": r.id, "role": r.role, "content": r.content, "proposal": bool(r.proposal),
                 "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
    finally:
        session.close()


def add_message(project_id: str, role: str, content: str, proposal: bool = False):
    session = get_session(init_db())
    try:
        session.add(ChatMessage(project_id=project_id, role=role, content=content, proposal=proposal))
        session.commit()
    finally:
        session.close()


def resolve_proposals(project_id: str):
    """La proposta in attesa e' stata applicata o scartata: nessun messaggio resta in sospeso."""
    session = get_session(init_db())
    try:
        session.query(ChatMessage).filter(ChatMessage.project_id == project_id,
                                          ChatMessage.proposal.is_(True)).update({"proposal": False})
        session.commit()
    finally:
        session.close()


def has_pending_proposal(project_id: str) -> bool:
    history = get_history(project_id)
    return bool(history) and history[-1]["role"] == "assistant" and history[-1]["proposal"]


def clear_history(project_id: str):
    session = get_session(init_db())
    try:
        session.query(ChatMessage).filter(ChatMessage.project_id == project_id).delete()
        session.commit()
    finally:
        session.close()


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


HISTORY_LIMIT = 10


def _parse_turn(raw: str) -> dict:
    """Legge la risposta strutturata del modello; se non e' JSON valido usa il testo senza codice."""
    text = (raw or "").strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = match.group(1) if match else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(candidate[start:end + 1])
            reply = str(data.get("reply", "")).strip()
            if reply:
                return {"reply": _strip_code(reply), "proposal": bool(data.get("proposal")),
                        "apply": bool(data.get("apply"))}
        except (ValueError, AttributeError):
            pass
    return {"reply": _strip_code(text) or "Non ho capito: puoi dirmelo in altre parole?", "proposal": False, "apply": False}


def _strip_code(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text).strip()


async def chat(project_id: str, message: str, document_ids: list[str], existing_schema: Optional[NormalizedSchema] = None) -> dict:
    """Un turno di conversazione. Restituisce {reply, proposal, apply}; non modifica lo schema."""
    doc_context = build_doc_context(project_id, document_ids)
    history = get_history(project_id)

    if not history:
        intro = "Ti aiuto a rifinire lo schema del database. Descrivi cosa vuoi cambiare o quali dati devi memorizzare"
        if doc_context:
            intro += ", tenendo conto dei documenti caricati"
        intro += "."
        add_message(project_id, "assistant", intro)
        history = get_history(project_id)

    pending = bool(history) and history[-1]["role"] == "assistant" and history[-1]["proposal"]
    add_message(project_id, "user", message)
    history = get_history(project_id)

    try:
        llm = _get_llm(temperature=0.3)

        schema_context = ""
        if existing_schema:
            tables = "; ".join(f"{t.name} ({', '.join(c.name for c in t.columns)})" for t in existing_schema.tables)
            schema_context = f"\nSchema attuale (sintesi): {tables}"
        schema_context += f"\nProposta in attesa di conferma: {'si' if pending else 'no'}"

        msg_history = []
        for h in history[-HISTORY_LIMIT:]:
            if h["role"] == "user":
                msg_history.append(HumanMessage(content=h["content"]))
            else:
                msg_history.append(AIMessage(content=_strip_code(h["content"])))

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + "\n\nContesto dei documenti caricati:\n{doc_context}\n{schema_context}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        chain = prompt | llm
        result = await chain.ainvoke({
            "doc_context": doc_context or "Nessun documento caricato.",
            "schema_context": schema_context,
            "history": msg_history[:-1],
            "input": message,
        })
        turn = _parse_turn(result.content)
    except Exception as e:
        log.error(f"Chat LLM call failed ({type(e).__name__})")
        raise AppException(detail="Chat generation failed", status_code=502) from e

    turn["apply"] = bool(turn["apply"] and pending)
    if turn["apply"]:
        turn["proposal"] = False
    add_message(project_id, "assistant", turn["reply"], proposal=turn["proposal"])
    return turn


APPLY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Sei un progettista di database. Ti do lo schema attuale e la conversazione con l'utente, che ha accettato "
               "le modifiche proposte. Restituisci lo schema COMPLETO aggiornato con quelle modifiche e nient'altro cambiato: "
               "stesso formato dello schema attuale, solo JSON grezzo, senza spiegazioni ne' markdown.\n"
               "Struttura: {{\"tables\": [...], \"relationships\": [...], \"description\": \"...\"}}\n"
               "Ogni relazione deve avere il campo \"type\": one_to_many, many_to_many oppure one_to_one. "
               "Le chiavi esterne devono riferirsi a tabelle e colonne esistenti."),
    ("system", "Schema attuale:\n{current}"),
    ("system", "Conversazione:\n{history}"),
    ("user", "Applica le modifiche accettate e restituisci lo schema completo in JSON."),
])


async def apply_proposal(project_id: str, existing_schema: NormalizedSchema) -> NormalizedSchema:
    """Dopo la conferma dell'utente: costruisce lo schema aggiornato dal JSON del modello. Non salva nulla."""
    history = [m for m in get_history(project_id)][-HISTORY_LIMIT:]
    history_text = "\n".join(f"{m['role']}: {_strip_code(m['content'])}" for m in history)
    try:
        llm = _get_llm(temperature=0.1)
        result = await (APPLY_PROMPT | llm).ainvoke({
            "current": json.dumps(existing_schema.model_dump(), ensure_ascii=False),
            "history": history_text,
        })
    except Exception as e:
        log.error(f"Applicazione della proposta fallita ({type(e).__name__})")
        raise AppException(detail="Non sono riuscito ad applicare le modifiche", status_code=502) from e
    schema = extract_schema_from_response(result.content)
    if schema is None or not schema.tables:
        meta = getattr(result, "response_metadata", None) or {}
        log.error(f"Schema aggiornato non valido: finish_reason={meta.get('finish_reason')}")
        raise AppException(detail="Non sono riuscito ad applicare le modifiche: riprova", status_code=502)
    resolve_proposals(project_id)
    return schema


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


def _close_open_json(raw: str) -> str:
    """Il modello a volte dimentica le ultime parentesi: le aggiunge, senza toccare il resto."""
    stack, in_string, escaped = [], False, False
    for ch in raw:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    return raw + "".join(reversed(stack)) if not in_string else raw


def _load_json(raw: str):
    try:
        return json.loads(raw)
    except ValueError:
        return json.loads(_close_open_json(raw))


def _try_build_schema(raw: str) -> NormalizedSchema | None:
    try:
        data = _load_json(raw)
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
