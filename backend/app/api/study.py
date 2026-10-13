"""Studio con partecipanti (RQ0/RQ3): percorso del partecipante e pannello del ricercatore.

Dietro RESEARCH_MODE. I partecipanti devono avere un account ma l'id utente non viene mai salvato: la persona e'
solo un id casuale con un codice di ritiro (intestazione `X-Study-Code`). Per limitare le iscrizioni a una per
account si salva solo un HMAC con sale dell'id utente, che si azzera al ritiro.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Header, Query
from fastapi.responses import Response

from app.api.benchmark_runs import researcher_only
from app.core.acl import ensure_user
from app.core.auth import get_current_user
from app.core.research import require_research
from app.services import research_study as study
from app.utils.exceptions import AppException

router = APIRouter(prefix="/api/study")

PARTICIPANT = [Depends(require_research), Depends(get_current_user)]
RESEARCHER = [Depends(require_research), Depends(researcher_only)]


def _run(fn, *args):
    try:
        return fn(*args)
    except study.StudyError as exc:
        raise AppException(detail=exc.detail, status_code=exc.status)


@router.get("/info", dependencies=PARTICIPANT)
def info():
    return {"consent_version": study.CONSENT_VERSION, "age_bands": study.AGE_BANDS, "roles": study.ROLES,
            "tlx_keys": study.TLX_KEYS}


@router.post("/participants", status_code=201, dependencies=PARTICIPANT)
def enroll(body: dict = Body(...), user: dict = Depends(get_current_user)):
    row = ensure_user(user)  # un account sospeso non puo' iscriversi (403)
    return _run(study.enroll, body.get("consent"), body.get("consent_version"), body.get("demographics"),
                study.account_hash(row.id))


def _code(header: str | None, body: dict | None) -> str | None:
    """Il codice del partecipante arriva nel corpo (`code`) o nell'intestazione `X-Study-Code`; mai nell'URL."""
    return header or (body or {}).get("code")


@router.post("/participants/{pid}/state", dependencies=PARTICIPANT)
def state(pid: str, body: dict = Body(default={}), x_study_code: str | None = Header(None)):
    return _run(study.get_state, pid, _code(x_study_code, body))


@router.post("/participants/{pid}/events", dependencies=PARTICIPANT)
def event(pid: str, body: dict = Body(...), x_study_code: str | None = Header(None)):
    return _run(study.add_event, pid, _code(x_study_code, body), str(body.get("type") or ""), body.get("data"))


@router.post("/participants/{pid}/schema/load", dependencies=PARTICIPANT)
def get_schema(pid: str, body: dict = Body(default={}), x_study_code: str | None = Header(None)):
    return _run(study.get_schema, pid, _code(x_study_code, body))


@router.put("/participants/{pid}/schema", dependencies=PARTICIPANT)
def put_schema(pid: str, body: dict = Body(...), x_study_code: str | None = Header(None)):
    return _run(study.save_schema, pid, _code(x_study_code, body), body)


@router.post("/participants/{pid}/task/complete", dependencies=PARTICIPANT)
def task_done(pid: str, body: dict = Body(default={}), x_study_code: str | None = Header(None)):
    return _run(study.complete_task, pid, _code(x_study_code, body))


@router.post("/participants/{pid}/nasa-tlx", dependencies=PARTICIPANT)
def tlx(pid: str, body: dict = Body(...), x_study_code: str | None = Header(None)):
    return _run(study.submit_response, pid, _code(x_study_code, body), "nasa_tlx", body)


@router.post("/participants/{pid}/sus", dependencies=PARTICIPANT)
def sus(pid: str, body: dict = Body(...), x_study_code: str | None = Header(None)):
    return _run(study.submit_response, pid, _code(x_study_code, body), "sus", body)


@router.post("/participants/{pid}/debrief", dependencies=PARTICIPANT)
def debrief(pid: str, body: dict = Body(default={}), x_study_code: str | None = Header(None)):
    return _run(study.submit_response, pid, _code(x_study_code, body), "debrief", body)


@router.post("/participants/{pid}/withdraw", dependencies=PARTICIPANT)
def withdraw(pid: str, body: dict = Body(default={}), x_study_code: str | None = Header(None)):
    return _run(study.withdraw, pid, _code(x_study_code, body))


# ------------------------------------------------------------------ ricercatore
@router.get("/admin/status", dependencies=RESEARCHER)
def status():
    return study.arm_status()


@router.get("/admin/export", dependencies=RESEARCHER)
def export(kind: str = Query("events", pattern="^(events|responses|participants)$"), wrap: bool = False):
    content = _run(study.export_csv, kind)
    name = f"studio-{kind}.csv"
    if wrap:
        return {"filename": name, "mime": "text/csv", "content": content}
    return Response(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/admin/erase", dependencies=RESEARCHER)
def erase(body: dict = Body(...), user: dict = Depends(researcher_only)):
    return _run(study.erase_by_code, str(body.get("code") or ""), user.get("sub"))
