"""Strumenti del ricercatore per i benchmark: run, confronti, coda, esportazione, diagnosi.

Tutto dietro RESEARCH_MODE (404 se spento) e riservato a admin e ruolo `aidb-researcher` (403 agli altri).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response

from app.core.acl import ensure_user
from app.core.auth import get_current_user
from app.core.research import require_research
from app.models.database import AdminAuditLog, get_session, init_db
from app.services import research_manifest, research_runs
from app.utils.exceptions import AppException
from app.utils.research import is_researcher

router = APIRouter(prefix="/api/research")


def researcher_only(user: dict = Depends(get_current_user)) -> dict:
    if not is_researcher(user):
        raise AppException(detail="Riservato a chi conduce la ricerca", status_code=403)
    ensure_user(user)
    return user


GUARD = [Depends(require_research), Depends(researcher_only)]


def _filters(dataset: str | None, condition: str | None, model: str | None, temperature: float | None,
             status: str | None = None) -> dict:
    return {"dataset": dataset or None, "condition": condition or None, "model": model or None,
            "temperature": temperature, "status": status or None}


@router.get("/meta", dependencies=GUARD)
def meta():
    return {
        "datasets": research_manifest.list_datasets(),
        "conditions": list(research_runs.CONDITIONS),
        "models": research_runs.available_models(),
        "temperatures": [0.0, 0.1, 0.5, 1.0],
        "cost_cap_usd": research_runs.cost_cap_usd(),
        "max_batch_runs": research_runs.MAX_BATCH_RUNS,
        "filters": research_runs.filter_options(),
        "software_revision": research_manifest.software_revision(),
    }


@router.get("/runs", dependencies=GUARD)
def runs(dataset: str | None = None, condition: str | None = None, model: str | None = None,
         temperature: float | None = None, status: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    return {"runs": research_runs.list_runs(limit=limit, **_filters(dataset, condition, model, temperature, status))}


@router.get("/runs/{run_id}", dependencies=GUARD)
def run_detail(run_id: str):
    run = research_runs.get_run(run_id)
    if run is None:
        raise AppException(detail="Run non trovato", status_code=404)
    return run


@router.get("/summary", dependencies=GUARD)
def summary(dataset: str | None = None, condition: str | None = None, model: str | None = None,
            temperature: float | None = None):
    return {"groups": research_runs.summarize(**{k: v for k, v in _filters(dataset, condition, model, temperature).items()
                                                  if k != "status"})}


def _batch_args(body: dict) -> tuple:
    return (body.get("datasets"), body.get("conditions"), body.get("model") or "", body.get("temperatures"),
            body.get("runs", 1))


@router.post("/estimate", dependencies=GUARD)
def estimate(body: dict = Body(...)):
    datasets, conditions, model, temperatures, runs_n = _batch_args(body)
    if not model:
        raise AppException(detail="Scegli il modello.", status_code=422)
    try:
        return research_runs.estimate_batch(datasets, conditions, model, temperatures, runs_n)
    except ValueError as exc:
        raise AppException(detail=str(exc), status_code=422)


@router.post("/batches", status_code=202, dependencies=GUARD)
def launch(body: dict = Body(...), user: dict = Depends(researcher_only)):
    datasets, conditions, model, temperatures, runs_n = _batch_args(body)
    if not model:
        raise AppException(detail="Scegli il modello.", status_code=422)
    if body.get("confirm_cost") is not True:
        raise AppException(detail="Conferma la stima del costo prima di avviare.", status_code=422)
    try:
        result = research_runs.enqueue_batch(datasets, conditions, model, temperatures, runs_n, user.get("sub"))
    except ValueError as exc:
        raise AppException(detail=str(exc), status_code=422)
    except PermissionError as exc:
        raise AppException(detail=str(exc), status_code=422)
    session = get_session(init_db())
    try:
        session.add(AdminAuditLog(actor_id=user.get("sub"), action="research_batch_started", target=result["batch_id"],
                                  detail={"runs": result["runs"], "model": model}))
        session.commit()
    finally:
        session.close()
    return result


@router.get("/queue", dependencies=GUARD)
def queue():
    return research_runs.queue_state()


@router.post("/runs/{run_id}/cancel", dependencies=GUARD)
def cancel(run_id: str):
    try:
        return {"status": research_runs.cancel_run(run_id)}
    except LookupError:
        raise AppException(detail="Run non trovato", status_code=404)
    except ValueError as exc:
        raise AppException(detail=str(exc), status_code=409)


@router.get("/export", dependencies=GUARD)
def export(format: str = Query("csv", pattern="^(csv|json)$"), wrap: bool = False, dataset: str | None = None,
           condition: str | None = None, model: str | None = None, temperature: float | None = None,
           status: str | None = None):
    filters = _filters(dataset, condition, model, temperature, status)
    if format == "csv":
        content, mime, name = research_runs.export_csv(**filters), "text/csv", "run-ricerca.csv"
    else:
        content = json.dumps(research_runs.export_json(**filters), ensure_ascii=False, indent=2, default=str)
        mime, name = "application/json", "run-ricerca.json"
    if wrap:
        return {"filename": name, "mime": mime, "content": content}
    return Response(content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/diagnosis", dependencies=GUARD)
def diagnosis(dataset: str = "university", condition: str = "full_llm", temperature: float = 0.5,
              model: str | None = None):
    return research_runs.diagnose(dataset=dataset, condition=condition, temperature=temperature, model=model or None)


@router.post("/import", dependencies=GUARD)
def import_reports(body: dict = Body(...), user: dict = Depends(researcher_only)):
    """Importa i report di run_benchmark.py; la cartella deve stare dentro `reports/`."""
    base = (Path("reports")).resolve()
    target = (base / str(body.get("path") or "")).resolve()
    if base != target and base not in target.parents:
        raise AppException(detail="Percorso non consentito", status_code=422)
    if not target.is_dir():
        raise AppException(detail="Cartella non trovata", status_code=404)
    return {"imported": research_runs.import_reports(target, user.get("sub"))}
