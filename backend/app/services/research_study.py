"""Studio con partecipanti: assegnazione ai bracci, risposte, eventi senza dati personali, ritiro e cancellazione.

Il partecipante e' un id casuale (pseudonimo) con un codice di ritiro che si mostra una sola volta; del codice si salva
solo l'hash. Nessun collegamento con l'utente autenticato, nessuna email, nessun indirizzo IP.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import secrets
import threading
import uuid

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.acl import utcnow_naive
from app.models.database import (
    AdminAuditLog, StudyEvent, StudyParticipant, StudyResponse, get_session, init_db,
)
from app.utils.research import stable_hash

ARMS = ("manual", "ai_only", "ai_interface")
CONSENT_VERSION = "1.0"
TARGET_PER_ARM = 20
STEPS = ("task", "tlx", "sus", "debrief", "done")

AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55+")
ROLES = ("studente", "sviluppatore", "analista", "docente", "altro")
EVENT_TYPES = ("task_start", "task_end", "schema_edit", "schema_export", "help_request", "page_view",
               "ai_prompt_sent", "ai_schema_accepted", "error")
TLX_KEYS = ("mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration")
SUS_ITEMS = 10

MAX_EVENTS_PER_PARTICIPANT = 5000

_assign_lock = threading.Lock()
_FORBIDDEN_WORDS = {"email", "mail", "ip", "name", "nome", "cognome", "user", "username", "token", "phone", "tel",
                    "telefono", "address", "indirizzo", "sub", "password"}
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


class StudyError(Exception):
    def __init__(self, detail: str, status: int = 422):
        super().__init__(detail)
        self.detail, self.status = detail, status


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def account_hash(user_id: str) -> str:
    """HMAC con sale dell'id utente: serve solo a impedire iscrizioni doppie, non e' reversibile."""
    salt = (settings.study_account_salt or "aidb-study-account").encode("utf-8")
    return hmac.new(salt, str(user_id).encode("utf-8"), hashlib.sha256).hexdigest()


def new_code() -> str:
    raw = secrets.token_hex(5).upper()  # 10 caratteri esadecimali
    return f"{raw[:5]}-{raw[5:]}"


# ------------------------------------------------------------------ dati ammessi
def clean_demographics(raw) -> dict:
    if not isinstance(raw, dict):
        raise StudyError("Compila il questionario iniziale.")
    out = {}
    if raw.get("age_band") not in AGE_BANDS:
        raise StudyError("Scegli la tua fascia di eta'.")
    out["age_band"] = raw["age_band"]
    if raw.get("role") not in ROLES:
        raise StudyError("Scegli il tuo ruolo.")
    out["role"] = raw["role"]
    for key, label in (("db_experience", "database"), ("ai_experience", "strumenti di intelligenza artificiale")):
        value = raw.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise StudyError(f"Indica la tua esperienza con {label} da 1 a 5.")
        out[key] = value
    return out


def clean_event_data(data) -> dict:
    """Solo valori semplici e brevi; chiavi e testi che somigliano a dati personali vengono scartati o oscurati."""
    if not isinstance(data, dict):
        return {}
    out = {}
    for key, value in list(data.items())[:20]:
        key = str(key)[:40]
        if "email" in key.lower() or _FORBIDDEN_WORDS & set(re.split(r"[^a-z]+", key.lower())):
            continue
        if isinstance(value, bool) or isinstance(value, (int, float)) or value is None:
            out[key] = value
        elif isinstance(value, str):
            text = _IP.sub("[omesso]", _EMAIL.sub("[omesso]", value))
            out[key] = text[:200]
    return out


def clean_manual_schema(raw) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("tables"), list):
        raise StudyError("Lo schema deve avere un elenco di tabelle.")
    tables = raw["tables"]
    if not 1 <= len(tables) <= 30:
        raise StudyError("Servono da 1 a 30 tabelle.")
    ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,59}$")
    out = []
    for t in tables:
        if not isinstance(t, dict) or not ident.match(str(t.get("name", ""))):
            raise StudyError("Ogni tabella ha bisogno di un nome valido (lettere, numeri e trattino basso).")
        cols = t.get("columns")
        if not isinstance(cols, list) or not 1 <= len(cols) <= 40:
            raise StudyError(f"La tabella {t['name']} deve avere da 1 a 40 colonne.")
        clean_cols = []
        for c in cols:
            if not isinstance(c, dict) or not ident.match(str(c.get("name", ""))):
                raise StudyError(f"Nome di colonna non valido nella tabella {t['name']}.")
            ref = c.get("references")
            if ref is not None and not (isinstance(ref, str) and re.match(r"^[A-Za-z_]\w{0,59}\.[A-Za-z_]\w{0,59}$", ref)):
                raise StudyError("Il riferimento deve avere la forma tabella.colonna.")
            clean_cols.append({"name": c["name"], "type": str(c.get("type") or "TEXT").upper()[:20],
                               "primary_key": bool(c.get("primary_key")), "nullable": c.get("nullable", True) is not False,
                               "references": ref})
        out.append({"name": t["name"], "columns": clean_cols})
    return {"tables": out}


def clean_tlx(raw) -> dict:
    if not isinstance(raw, dict) or any(k not in raw for k in TLX_KEYS):
        raise StudyError("Completa tutte le sei dimensioni.")
    scores = {k: raw[k] for k in TLX_KEYS}
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v > 100 or v % 5 != 0 for v in scores.values()):
        raise StudyError("I punteggi vanno da 0 a 100, a passi di 5.")
    return {**scores, "score": round(sum(scores.values()) / len(scores), 2)}


def clean_sus(raw) -> dict:
    scores = raw.get("scores") if isinstance(raw, dict) else None
    if not isinstance(scores, list) or len(scores) != SUS_ITEMS:
        raise StudyError("Rispondi a tutte e 10 le domande.")
    if any(isinstance(s, bool) or not isinstance(s, int) or not 1 <= s <= 5 for s in scores):
        raise StudyError("Ogni risposta va da 1 a 5.")
    total = sum((s - 1) if i % 2 == 0 else (5 - s) for i, s in enumerate(scores)) * 2.5
    return {"scores": scores, "score": total}


def clean_debrief(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    comment = _IP.sub("[omesso]", _EMAIL.sub("[omesso]", str(raw.get("comment") or "")))[:1000]
    return {"comment": comment}


# ------------------------------------------------------------------ partecipanti
def _balanced_arm(session) -> str:
    counts = {a: 0 for a in ARMS}
    for (arm,) in session.query(StudyParticipant.arm).filter(StudyParticipant.withdrawn_at.is_(None)).all():
        counts[arm] = counts.get(arm, 0) + 1
    low = min(counts.values())
    return secrets.choice([a for a in ARMS if counts[a] == low])


def enroll(consent: bool, consent_version: str | None, demographics, account: str | None = None) -> dict:
    if consent is not True:
        raise StudyError("Serve il tuo consenso per partecipare.")
    if consent_version != CONSENT_VERSION:
        raise StudyError("L'informativa e' stata aggiornata: ricarica la pagina e rileggila.")
    demo = clean_demographics(demographics)
    code = new_code()
    session = get_session(init_db())
    try:
        with _assign_lock:
            if account and session.query(StudyParticipant.id).filter(
                    StudyParticipant.account_hash == account, StudyParticipant.withdrawn_at.is_(None)).first():
                raise StudyError("Risulti gia' iscritto allo studio. Per ripartire ritira prima la partecipazione.", 409)
            arm = _balanced_arm(session)
            p = StudyParticipant(id=uuid.uuid4().hex, code_hash=hash_code(code), arm=arm,
                                 consent_version=CONSENT_VERSION, consented_at=utcnow_naive(),
                                 demographics=demo, step="task", account_hash=account)
            session.add(p)
            try:
                session.commit()
            except IntegrityError:  # indice unico parziale: iscrizione concorrente dello stesso account
                session.rollback()
                raise StudyError("Risulti gia' iscritto allo studio.", 409)
            return {"participant_id": p.id, "code": code, "arm": arm, "step": p.step}
    finally:
        session.close()


def _load(session, participant_id: str, code: str | None) -> StudyParticipant:
    p = session.get(StudyParticipant, participant_id) if participant_id else None
    if p is None or not code or not hmac.compare_digest(p.code_hash, hash_code(code)):
        raise StudyError("Partecipante non trovato", 404)
    if p.withdrawn_at is not None:
        raise StudyError("Hai ritirato la tua partecipazione.", 410)
    return p


def get_state(participant_id: str, code: str | None) -> dict:
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        done = {r.kind for r in session.query(StudyResponse).filter_by(participant_id=p.id).all()}
        return {"participant_id": p.id, "arm": p.arm, "step": p.step, "responses": sorted(done)}
    finally:
        session.close()


def add_event(participant_id: str, code: str | None, etype: str, data) -> dict:
    if etype not in EVENT_TYPES:
        raise StudyError("Tipo di evento non valido.")
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        if session.query(StudyEvent).filter_by(participant_id=p.id).count() >= MAX_EVENTS_PER_PARTICIPANT:
            raise StudyError("Limite di eventi raggiunto per questo partecipante.", 429)
        session.add(StudyEvent(participant_id=p.id, type=etype, data=clean_event_data(data)))
        session.commit()
        return {"status": "saved"}
    finally:
        session.close()


def _upsert(session, pid: str, kind: str, data: dict) -> None:
    row = session.query(StudyResponse).filter_by(participant_id=pid, kind=kind).first()
    if row is None:
        session.add(StudyResponse(participant_id=pid, kind=kind, data=data))
    else:
        row.data = data


def save_schema(participant_id: str, code: str | None, raw) -> dict:
    schema = clean_manual_schema(raw)
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        if p.arm != "manual":
            raise StudyError("L'editor di schema e' solo per il braccio manuale.", 409)
        digest = stable_hash(schema)
        _upsert(session, p.id, "schema", {**schema, "schema_hash": digest})
        session.add(StudyEvent(participant_id=p.id, type="schema_edit",
                               data={"tables": len(schema["tables"]), "schema_hash": digest[:16]}))
        session.commit()
        return {"status": "saved", "schema_hash": digest}
    finally:
        session.close()


def get_schema(participant_id: str, code: str | None) -> dict:
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        row = session.query(StudyResponse).filter_by(participant_id=p.id, kind="schema").first()
        return {"tables": row.data["tables"]} if row else {"tables": []}
    finally:
        session.close()


def _advance(session, p: StudyParticipant, expected: str, nxt: str) -> None:
    """Avanza il passo con un UPDATE condizionale: due richieste concorrenti non lo completano due volte."""
    values = {"step": nxt}
    if nxt == "done":
        values["completed_at"] = utcnow_naive()
    changed = session.execute(update(StudyParticipant).where(
        StudyParticipant.id == p.id, StudyParticipant.step == expected,
        StudyParticipant.withdrawn_at.is_(None)).values(**values)).rowcount
    if not changed:
        session.rollback()
        raise StudyError("Questo passo non e' ancora disponibile o l'hai gia' completato.", 409)
    session.refresh(p)


def complete_task(participant_id: str, code: str | None) -> dict:
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        _advance(session, p, "task", "tlx")
        session.add(StudyEvent(participant_id=p.id, type="task_end", data={}))
        session.commit()
        return {"step": p.step}
    finally:
        session.close()


def submit_response(participant_id: str, code: str | None, kind: str, raw) -> dict:
    cleaners = {"nasa_tlx": (clean_tlx, "tlx", "sus"), "sus": (clean_sus, "sus", "debrief"),
                "debrief": (lambda r: clean_debrief(r), "debrief", "done")}
    clean, expected, nxt = cleaners[kind]
    data = clean(raw)
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        _advance(session, p, expected, nxt)
        _upsert(session, p.id, kind, data)
        session.commit()
        return {"step": p.step, **({"score": data["score"]} if "score" in data else {})}
    finally:
        session.close()


# ------------------------------------------------------------------ ritiro e cancellazione
def _erase(session, p: StudyParticipant) -> None:
    session.query(StudyEvent).filter_by(participant_id=p.id).delete()
    session.query(StudyResponse).filter_by(participant_id=p.id).delete()
    p.demographics = None
    p.account_hash = None  # il collegamento con l'account non serve piu'
    p.withdrawn_at = utcnow_naive()
    p.step = "withdrawn"


def withdraw(participant_id: str, code: str | None) -> dict:
    session = get_session(init_db())
    try:
        p = _load(session, participant_id, code)
        _erase(session, p)
        session.commit()
        return {"status": "withdrawn"}
    finally:
        session.close()


def erase_by_code(code: str, actor_id: str | None) -> dict:
    """Cancellazione su richiesta: la persona comunica il codice al ricercatore, che cancella i suoi dati."""
    session = get_session(init_db())
    try:
        p = session.query(StudyParticipant).filter_by(code_hash=hash_code(code or "")).first()
        if p is None:
            raise StudyError("Nessun partecipante con questo codice.", 404)
        already = p.withdrawn_at is not None
        if not already:
            _erase(session, p)
        session.add(AdminAuditLog(actor_id=actor_id or "sconosciuto", action="study_participant_erased",
                                  target=p.id, detail={"already_withdrawn": already}))
        session.commit()
        return {"status": "erased", "participant_id": p.id, "already_withdrawn": already}
    finally:
        session.close()


# ------------------------------------------------------------------ pannello ricercatore
def arm_status() -> dict:
    session = get_session(init_db())
    try:
        rows = session.query(StudyParticipant).all()
    finally:
        session.close()
    arms = []
    for arm in ARMS:
        mine = [r for r in rows if r.arm == arm]
        active = [r for r in mine if r.withdrawn_at is None]
        arms.append({"arm": arm, "enrolled": len(mine), "active": len(active),
                     "completed": sum(1 for r in active if r.completed_at is not None),
                     "withdrawn": len(mine) - len(active), "target": TARGET_PER_ARM})
    actives = [a["active"] for a in arms]
    return {"arms": arms, "total": len(rows), "balanced": max(actives) - min(actives) <= 1,
            "consent_version": CONSENT_VERSION}


def _csv(fields: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_csv(kind: str) -> str:
    session = get_session(init_db())
    try:
        arms = {p.id: p for p in session.query(StudyParticipant).all()}
        if kind == "events":
            rows = []
            for e in session.query(StudyEvent).order_by(StudyEvent.created_at, StudyEvent.id).all():
                p = arms.get(e.participant_id)
                rows.append({"participant_id": e.participant_id, "arm": p.arm if p else "", "type": e.type,
                             "created_at": e.created_at.isoformat() if e.created_at else "",
                             "data": json.dumps(e.data or {}, ensure_ascii=False, sort_keys=True)})
            return _csv(["participant_id", "arm", "type", "created_at", "data"], rows)
        responses: dict[str, dict[str, dict]] = {}
        for r in session.query(StudyResponse).all():
            responses.setdefault(r.participant_id, {})[r.kind] = r.data
        if kind == "responses":
            rows = []
            for pid, kinds in sorted(responses.items()):
                for k, data in sorted(kinds.items()):
                    rows.append({"participant_id": pid, "arm": arms[pid].arm if pid in arms else "", "kind": k,
                                 "score": data.get("score", ""), "data": json.dumps(data, ensure_ascii=False, sort_keys=True)})
            return _csv(["participant_id", "arm", "kind", "score", "data"], rows)
        if kind == "participants":
            rows = []
            for p in sorted(arms.values(), key=lambda x: (x.created_at or utcnow_naive(), x.id)):
                demo = p.demographics or {}
                got = responses.get(p.id, {})
                rows.append({"participant_id": p.id, "arm": p.arm, "consent_version": p.consent_version or "",
                             "step": p.step, "completed": p.completed_at is not None,
                             "withdrawn": p.withdrawn_at is not None, "age_band": demo.get("age_band", ""),
                             "role": demo.get("role", ""), "db_experience": demo.get("db_experience", ""),
                             "ai_experience": demo.get("ai_experience", ""),
                             "nasa_tlx": got.get("nasa_tlx", {}).get("score", ""), "sus": got.get("sus", {}).get("score", ""),
                             "schema_hash": got.get("schema", {}).get("schema_hash", "")})
            return _csv(["participant_id", "arm", "consent_version", "step", "completed", "withdrawn", "age_band", "role",
                         "db_experience", "ai_experience", "nasa_tlx", "sus", "schema_hash"], rows)
        raise StudyError("Tipo di esportazione non valido.")
    finally:
        session.close()
