"""Run di ricerca: coda semplice, esecuzione, stima del costo, riepiloghi con intervalli, esportazione e diagnosi.

L'esecuzione passa da un "executor" sostituibile: in produzione guida `BenchmarkRunner` (servizi reali), nei test
si usa una funzione simulata, cosi' non si chiama mai un LLM vero.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import tempfile
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Callable

from app.core.acl import utcnow_naive
from app.models.database import ResearchRun, get_session, init_db
from app.services import research_manifest
from app.services.research_stats import bootstrap_ci, safe_mean
from app.utils.logger import log

CONDITIONS = ("full_llm", "baseline")
# Prezzi indicativi in USD per milione di token (ingresso, uscita): servono solo alla stima e ai costi dei log.
PRICES = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.0-flash": (0.10, 0.40),
}
DEFAULT_PRICE = (0.30, 2.50)
MAX_BATCH_RUNS = 60
STALE_MINUTES = 90
METRICS = ("f1", "precision", "recall", "value_accuracy", "judge_score")


def cost_cap_usd() -> float:
    try:
        return float(os.getenv("RESEARCH_COST_CAP_USD", "25"))
    except ValueError:
        return 25.0


def price_for(model: str) -> tuple[float, float]:
    return PRICES.get(model, DEFAULT_PRICE)


def cost_from_tokens(model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
    if tokens_in is None and tokens_out is None:
        return None
    pin, pout = price_for(model)
    return round(((tokens_in or 0) * pin + (tokens_out or 0) * pout) / 1_000_000, 6)


def available_models() -> list[dict]:
    from app.core.llm import get_llm_info
    info = {}
    try:
        info = get_llm_info()
    except Exception:
        pass
    names = list(PRICES)
    current = info.get("model")
    if current and current not in names:
        names.insert(0, current)
    return [{"model": m, "price_in_per_mtok": price_for(m)[0], "price_out_per_mtok": price_for(m)[1],
             "current": m == current} for m in names]


def current_provider() -> str | None:
    try:
        from app.core.llm import get_llm_info
        return get_llm_info().get("provider")
    except Exception:
        return None


# ------------------------------------------------------------------ stima del costo
def estimate_run(dataset: str, condition: str, model: str) -> dict:
    """Stima grezza: ~4 caratteri per token, piu' prompt fissi; uscita fissa per schema e popolamento."""
    chars = research_manifest.dataset_source_chars(dataset)
    base_in = chars / 4 + 1500
    tokens_in = int(base_in * (2 if condition == "full_llm" else 1) + 1000)
    tokens_out = 6000 if condition == "full_llm" else 4000
    return {"tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_from_tokens(model, tokens_in, tokens_out)}


def validate_batch(datasets, conditions, temperatures, runs: int) -> tuple[list[str], list[str], list[float], int]:
    known = research_manifest.list_datasets()
    datasets = list(dict.fromkeys(datasets or []))
    conditions = list(dict.fromkeys(conditions or []))
    temperatures = list(dict.fromkeys(float(t) for t in (temperatures or [])))
    if not datasets or any(d not in known for d in datasets):
        raise ValueError("Dataset non valido.")
    if not conditions or any(c not in CONDITIONS for c in conditions):
        raise ValueError("Condizione non valida.")
    if not temperatures or any(t < 0 or t > 2 for t in temperatures):
        raise ValueError("La temperatura deve essere tra 0 e 2.")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1 or runs > 20:
        raise ValueError("Le ripetizioni devono essere tra 1 e 20.")
    if len(datasets) * len(conditions) * len(temperatures) * runs > MAX_BATCH_RUNS:
        raise ValueError(f"Troppi run in un solo lancio (massimo {MAX_BATCH_RUNS}).")
    return datasets, conditions, temperatures, runs


def estimate_batch(datasets, conditions, model: str, temperatures, runs: int) -> dict:
    datasets, conditions, temperatures, runs = validate_batch(datasets, conditions, temperatures, runs)
    tin = tout = 0
    for d in datasets:
        for c in conditions:
            one = estimate_run(d, c, model)
            tin += one["tokens_in"] * len(temperatures) * runs
            tout += one["tokens_out"] * len(temperatures) * runs
    total = len(datasets) * len(conditions) * len(temperatures) * runs
    cost = cost_from_tokens(model, tin, tout) or 0.0
    cap = cost_cap_usd()
    return {"runs": total, "tokens_in": tin, "tokens_out": tout, "cost_usd": round(cost, 4),
            "cap_usd": cap, "over_cap": cost > cap, "approximate": True}


# ------------------------------------------------------------------ serializzazione
def run_to_dict(r: ResearchRun, detail: bool = False) -> dict:
    out = {
        "id": r.id, "batch_id": r.batch_id, "dataset": r.dataset, "condition": r.condition,
        "provider": r.provider, "model": r.model, "temperature": r.temperature, "run_index": r.run_index,
        "status": r.status, "cancel_requested": bool(r.cancel_requested),
        "f1": r.f1, "precision": r.precision, "recall": r.recall,
        "value_accuracy": r.value_accuracy, "judge_score": r.judge_score,
        "tokens_in": r.tokens_in, "tokens_out": r.tokens_out, "cost_usd": r.cost_usd, "latency_s": r.latency_s,
        "error": r.error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }
    if detail:
        out.update({"per_table": r.per_table, "schema": r.schema_json, "manifest": r.manifest})
    return out


def value_accuracy_from(per_table: dict | None) -> float | None:
    """Celle corrette (esatte o equivalenti per tipo) sul totale delle celle confrontate."""
    if not per_table:
        return None
    good = bad = 0
    for t in per_table.values():
        good += int(t.get("exact", 0)) + int(t.get("type_consistent", 0))
        bad += (int(t.get("null_in_source", 0)) + int(t.get("wrong_value", 0))
                + int(t.get("fk_violations", 0)) + int(t.get("type_mismatch", 0)))
    return round(good / (good + bad), 4) if good + bad else None


def _apply_filters(query, dataset=None, condition=None, model=None, temperature=None, status=None, batch_id=None):
    if dataset:
        query = query.filter(ResearchRun.dataset == dataset)
    if condition:
        query = query.filter(ResearchRun.condition == condition)
    if model:
        query = query.filter(ResearchRun.model == model)
    if temperature is not None:
        query = query.filter(ResearchRun.temperature.between(temperature - 1e-6, temperature + 1e-6))
    if status:
        query = query.filter(ResearchRun.status == status)
    if batch_id:
        query = query.filter(ResearchRun.batch_id == batch_id)
    return query


def list_runs(limit: int = 500, **filters) -> list[dict]:
    session = get_session(init_db())
    try:
        q = _apply_filters(session.query(ResearchRun), **filters)
        rows = q.order_by(ResearchRun.created_at.desc(), ResearchRun.id).limit(max(1, min(limit, 2000))).all()
        return [run_to_dict(r) for r in rows]
    finally:
        session.close()


def get_run(run_id: str) -> dict | None:
    session = get_session(init_db())
    try:
        r = session.get(ResearchRun, run_id)
        return run_to_dict(r, detail=True) if r else None
    finally:
        session.close()


def filter_options() -> dict:
    session = get_session(init_db())
    try:
        def distinct(col):
            return sorted(v for (v,) in session.query(col).distinct().all() if v is not None)
        return {"datasets": distinct(ResearchRun.dataset), "conditions": distinct(ResearchRun.condition),
                "models": distinct(ResearchRun.model), "temperatures": distinct(ResearchRun.temperature)}
    finally:
        session.close()


# ------------------------------------------------------------------ riepilogo con intervalli
def summarize(**filters) -> list[dict]:
    """Un gruppo per (dataset, condizione, modello, temperatura) sui run completati."""
    filters["status"] = "done"
    session = get_session(init_db())
    try:
        rows = _apply_filters(session.query(ResearchRun), **filters).all()
    finally:
        session.close()
    groups: dict[tuple, list[ResearchRun]] = {}
    for r in rows:
        groups.setdefault((r.dataset, r.condition, r.model, r.temperature), []).append(r)
    out = []
    for (dataset, condition, model, temperature), items in sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        entry = {"dataset": dataset, "condition": condition, "model": model, "temperature": temperature,
                 "n_runs": len(items)}
        for metric in METRICS:
            entry[metric] = bootstrap_ci(getattr(r, metric) for r in items)
        entry["cost_usd_mean"] = safe_mean(r.cost_usd for r in items)
        entry["cost_usd_total"] = round(sum(r.cost_usd or 0 for r in items), 6)
        entry["latency_s_mean"] = safe_mean(r.latency_s for r in items)
        entry["tokens_in_mean"] = safe_mean(r.tokens_in for r in items)
        entry["tokens_out_mean"] = safe_mean(r.tokens_out for r in items)
        out.append(entry)
    return out


# ------------------------------------------------------------------ esportazione
EXPORT_FIELDS = ["id", "batch_id", "dataset", "condition", "provider", "model", "temperature", "run_index", "status",
                 "f1", "precision", "recall", "value_accuracy", "judge_score", "tokens_in", "tokens_out",
                 "cost_usd", "latency_s", "software_revision", "dataset_hash", "prompts_hash",
                 "created_at", "finished_at"]


def export_csv(**filters) -> str:
    runs = []
    session = get_session(init_db())
    try:
        rows = _apply_filters(session.query(ResearchRun), **filters).order_by(ResearchRun.created_at, ResearchRun.id).all()
        for r in rows:
            d = run_to_dict(r)
            m = r.manifest or {}
            d.update({"software_revision": m.get("software_revision"), "dataset_hash": m.get("dataset_hash"),
                      "prompts_hash": m.get("prompts_hash")})
            runs.append(d)
    finally:
        session.close()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(runs)
    return buf.getvalue()


def export_json(**filters) -> dict:
    session = get_session(init_db())
    try:
        rows = _apply_filters(session.query(ResearchRun), **filters).order_by(ResearchRun.created_at, ResearchRun.id).all()
        runs = [run_to_dict(r, detail=True) for r in rows]
    finally:
        session.close()
    return {"exported_at": utcnow_naive().isoformat() + "Z", "runs": runs, "summary": summarize(**filters)}


# ------------------------------------------------------------------ coda
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()
_executor: Callable[[dict], dict] | None = None


def set_executor(fn: Callable[[dict], dict] | None) -> None:
    """Sostituisce l'esecutore dei run (usato dai test per simulare l'LLM)."""
    global _executor
    _executor = fn


def enqueue_batch(datasets, conditions, model: str, temperatures, runs: int, user_id: str | None,
                  provider: str | None = None) -> dict:
    datasets, conditions, temperatures, runs = validate_batch(datasets, conditions, temperatures, runs)
    estimate = estimate_batch(datasets, conditions, model, temperatures, runs)
    if estimate["over_cap"]:
        raise PermissionError(f"Costo stimato {estimate['cost_usd']} USD oltre il tetto di {estimate['cap_usd']} USD.")
    batch_id = str(uuid.uuid4())
    session = get_session(init_db())
    try:
        provider = provider or current_provider()
        ids = []
        for d in datasets:
            for c in conditions:
                for t in temperatures:
                    for i in range(1, runs + 1):
                        row = ResearchRun(batch_id=batch_id, dataset=d, condition=c, provider=provider, model=model,
                                          temperature=t, run_index=i, status="queued", created_by=user_id)
                        session.add(row)
                        ids.append(1)
        session.commit()
    finally:
        session.close()
    start_worker()
    return {"batch_id": batch_id, "runs": len(ids), "estimate": estimate}


def queue_state() -> dict:
    recover_stale()
    session = get_session(init_db())
    try:
        active = session.query(ResearchRun).filter(ResearchRun.status.in_(("queued", "running"))) \
            .order_by(ResearchRun.created_at, ResearchRun.id).all()
        recent = session.query(ResearchRun).filter(ResearchRun.status.in_(("done", "failed", "cancelled"))) \
            .order_by(ResearchRun.finished_at.desc()).limit(10).all()
        return {"active": [run_to_dict(r) for r in active], "recent": [run_to_dict(r) for r in recent],
                "queued": sum(1 for r in active if r.status == "queued"),
                "running": sum(1 for r in active if r.status == "running")}
    finally:
        session.close()


def recover_stale() -> int:
    """Run 'running' fermi da troppo tempo (processo riavviato) risultano falliti."""
    limit = utcnow_naive() - timedelta(minutes=STALE_MINUTES)
    session = get_session(init_db())
    try:
        rows = session.query(ResearchRun).filter(ResearchRun.status == "running", ResearchRun.started_at < limit).all()
        for r in rows:
            r.status, r.error, r.finished_at = "failed", "Interrotto: il processo non ha risposto.", utcnow_naive()
        session.commit()
        return len(rows)
    finally:
        session.close()


def cancel_run(run_id: str) -> str:
    """Restituisce 'cancelled' (era in coda), 'cancelling' (in esecuzione) o lancia ValueError/LookupError."""
    session = get_session(init_db())
    try:
        r = session.get(ResearchRun, run_id)
        if r is None:
            raise LookupError("Run non trovato")
        if r.status == "queued":
            r.status, r.finished_at = "cancelled", utcnow_naive()
            session.commit()
            return "cancelled"
        if r.status == "running":
            r.cancel_requested = True
            session.commit()
            return "cancelling"
        raise ValueError("Il run e' gia' concluso.")
    finally:
        session.close()


def start_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_worker_loop, name="research-runs", daemon=True)
        _worker.start()


def wait_idle(timeout: float = 30.0) -> bool:
    thread = _worker
    if thread is not None:
        thread.join(timeout)
        return not thread.is_alive()
    return True


def _claim_next() -> dict | None:
    session = get_session(init_db())
    try:
        r = session.query(ResearchRun).filter(ResearchRun.status == "queued") \
            .order_by(ResearchRun.created_at, ResearchRun.id).first()
        if r is None:
            return None
        r.status, r.started_at = "running", utcnow_naive()
        session.commit()
        return {"id": r.id, "dataset": r.dataset, "condition": r.condition, "model": r.model,
                "provider": r.provider, "temperature": r.temperature, "run_index": r.run_index}
    finally:
        session.close()


def _worker_loop() -> None:
    while True:
        try:
            job = _claim_next()
        except Exception as exc:  # database non raggiungibile: il worker si ferma, un nuovo lancio lo riavvia
            log.warning(f"Coda ricerca: lettura fallita ({type(exc).__name__})")
            return
        if job is None:
            return
        _execute(job)


def _execute(job: dict) -> None:
    started = time.monotonic()
    result: dict = {}
    error = None
    try:
        executor = _executor or real_executor
        result = executor(dict(job)) or {}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:500]
    elapsed = time.monotonic() - started
    session = get_session(init_db())
    try:
        r = session.get(ResearchRun, job["id"])
        if r is None:
            return
        r.finished_at = utcnow_naive()
        if r.cancel_requested:
            r.status = "cancelled"
        elif error or result.get("error"):
            r.status, r.error = "failed", error or str(result.get("error"))[:500]
        else:
            per_table = result.get("per_table")
            r.status = "done"
            r.precision, r.recall, r.f1 = result.get("precision"), result.get("recall"), result.get("f1")
            r.per_table = per_table
            r.value_accuracy = result.get("value_accuracy", value_accuracy_from(per_table))
            r.judge_score = result.get("judge_score")
            r.tokens_in, r.tokens_out = result.get("tokens_in"), result.get("tokens_out")
            r.cost_usd = result.get("cost_usd", cost_from_tokens(r.model, r.tokens_in, r.tokens_out))
            r.latency_s = round(result.get("latency_s", elapsed), 3)
            r.schema_json = result.get("schema")
            r.manifest = research_manifest.build_manifest(job, {
                "alignment": result.get("alignment"), "executor": result.get("executor", "custom"),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.finished_at.isoformat()})
        session.commit()
    finally:
        session.close()


# ------------------------------------------------------------------ esecutore reale
_PROVIDER_MODEL_SETTING = {"vertex": "vertex_model", "openai": "openai_model", "google": "google_model",
                           "groq": "groq_model", "openrouter": "openrouter_model"}
_usage = {"in": 0, "out": 0}
_real_lock = threading.Lock()


def real_executor(job: dict) -> dict:
    """Esegue un run con i servizi veri (BenchmarkRunner). Un solo run reale alla volta."""
    from app.config import settings
    from app.core import llm
    import run_benchmark  # script alla radice di backend/

    captured: dict = {}

    class _Runner(run_benchmark.BenchmarkRunner):
        def _evaluate(self, project_id, dataset, alignment=None):
            out = super()._evaluate(project_id, dataset, alignment)
            captured["evaluation"] = out[1]
            try:
                captured["schema"] = self.schema_svc.get_schema(project_id).model_dump()
            except Exception:
                captured["schema"] = None
            return out

    original_log = llm._log_usage
    attr = _PROVIDER_MODEL_SETTING.get(job.get("provider") or settings.llm_provider)
    previous_model = getattr(settings, attr, None) if attr else None

    def counting_log(result):
        usage = getattr(result, "usage_metadata", None) or {}
        _usage["in"] += int(usage.get("input_tokens") or 0)
        _usage["out"] += int(usage.get("output_tokens") or 0)
        original_log(result)

    with _real_lock, tempfile.TemporaryDirectory() as tmp:
        _usage.update({"in": 0, "out": 0})
        llm._log_usage = counting_log
        if attr:
            setattr(settings, attr, job["model"])
        try:
            runner = _Runner([job["dataset"]], [job["condition"]], 1, Path(tmp), adjudicate=True,
                             temperature=job["temperature"])
            started = time.monotonic()
            record = asyncio.run(runner._run_one(job["dataset"], job["condition"], job["run_index"]))
            latency = time.monotonic() - started
        finally:
            llm._log_usage = original_log
            if attr and previous_model is not None:
                setattr(settings, attr, previous_model)
        tokens = dict(_usage)
    if record.get("status") != "ok":
        return {"error": record.get("error") or "Run non riuscito"}
    evaluation = captured.get("evaluation") or {}
    judge = None
    scores = (record.get("adjudication") or {}).get("scores") or {}
    if scores.get("value_accuracy") is not None:
        judge = round(scores["value_accuracy"] / 100, 4)
    return {
        "precision": record["global_precision"], "recall": record["global_recall"], "f1": record["global_f1"],
        "per_table": evaluation.get("per_table"), "judge_score": judge, "schema": captured.get("schema"),
        "tokens_in": tokens["in"], "tokens_out": tokens["out"], "latency_s": latency,
        "alignment": record.get("alignment"), "executor": "benchmark_runner",
    }


# ------------------------------------------------------------------ importazione dei report della riga di comando
def import_reports(root: Path, user_id: str | None = None) -> int:
    """Importa i `runNN.json` scritti da run_benchmark.py (nessun duplicato per dataset/condizione/temperatura/indice)."""
    count = 0
    session = get_session(init_db())
    try:
        for path in sorted(root.rglob("run*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict) or not rec.get("dataset") or not rec.get("condition"):
                continue
            model = rec.get("model") or "sconosciuto"
            exists = session.query(ResearchRun).filter_by(
                dataset=rec["dataset"], condition=rec["condition"], run_index=rec.get("run", 1),
                temperature=rec.get("temperature"), model=model, status="done").first()
            if exists or rec.get("status") != "ok":
                continue
            scores = ((rec.get("adjudication") or {}).get("scores")) or {}
            session.add(ResearchRun(
                dataset=rec["dataset"], condition=rec["condition"], model=model, provider=rec.get("provider"),
                temperature=rec.get("temperature"), run_index=rec.get("run", 1), status="done",
                precision=rec.get("global_precision"), recall=rec.get("global_recall"), f1=rec.get("global_f1"),
                judge_score=(scores["value_accuracy"] / 100 if scores.get("value_accuracy") is not None else None),
                manifest=research_manifest.build_manifest(
                    {"dataset": rec["dataset"], "condition": rec["condition"], "model": model,
                     "provider": rec.get("provider"), "temperature": rec.get("temperature"),
                     "run_index": rec.get("run", 1)}, {"alignment": rec.get("alignment"), "executor": "import"}),
                created_by=user_id, finished_at=utcnow_naive()))
            count += 1
        session.commit()
    finally:
        session.close()
    return count


# ------------------------------------------------------------------ diagnosi (7.1)
def attribute_loss(per_table: dict | None, alignment: dict | None) -> dict:
    """Perdita di F1 per tabella (1 - F1) divisa tra schema e popolamento.

    Schema: la tabella gold non ha corrispondente, oppure alcune sue colonne non sono state generate (quota di colonne
    mancanti, al massimo la perdita della tabella). Il resto e' popolamento. Senza allineamento (condizione baseline,
    schema gold applicato) tutta la perdita e' di popolamento. E' un'approssimazione, dichiarata come tale.
    """
    out = {}
    align = alignment or {}
    unmatched_tables = set(align.get("unmatched_tables") or [])
    unmatched_cols = align.get("unmatched_columns") or {}
    matched_cols = align.get("columns") or {}
    for name, metrics in (per_table or {}).items():
        loss = round(1 - float(metrics.get("f1") or 0.0), 4)
        if name in unmatched_tables:
            schema_loss = loss
        else:
            missing = len(unmatched_cols.get(name) or [])
            total = missing + len(matched_cols.get(name) or {})
            schema_loss = round(min(loss, missing / total), 4) if total and missing else 0.0
        out[name] = {"f1": metrics.get("f1"), "loss": loss, "schema_loss": schema_loss,
                     "population_loss": round(loss - schema_loss, 4)}
    return out


def diagnose(dataset: str = "university", condition: str = "full_llm", temperature: float = 0.5,
             model: str | None = None, top: int = 3) -> dict:
    session = get_session(init_db())
    try:
        q = _apply_filters(session.query(ResearchRun), dataset=dataset, condition=condition, model=model,
                           temperature=temperature, status="done").filter(ResearchRun.f1.isnot(None))
        rows = q.all()
    finally:
        session.close()
    base = {"dataset": dataset, "condition": condition, "temperature": temperature, "model": model, "n_runs": len(rows)}
    if len(rows) < 2:
        return {**base, "available": False, "reason": "Servono almeno due run completati con questi parametri."}
    rows.sort(key=lambda r: (-(r.f1 or 0), r.id))
    top = max(1, min(top, len(rows) // 2))
    best, worst = rows[:top], rows[-top:][::-1]
    attributions = {r.id: attribute_loss(r.per_table, (r.manifest or {}).get("alignment")) for r in rows}

    def run_view(r: ResearchRun) -> dict:
        att = attributions[r.id]
        return {"id": r.id, "run_index": r.run_index, "model": r.model, "f1": r.f1,
                "tables": {t: v["f1"] for t, v in att.items()}}

    tables = sorted({t for a in attributions.values() for t in a})
    per_table = []
    for t in tables:
        def avg(group, key):
            vals = [attributions[r.id][t][key] for r in group if t in attributions[r.id]]
            return round(sum(vals) / len(vals), 4) if vals else None
        best_f1 = [attributions[r.id][t]["f1"] for r in best if t in attributions[r.id]]
        worst_f1 = [attributions[r.id][t]["f1"] for r in worst if t in attributions[r.id]]
        bf = round(sum(best_f1) / len(best_f1), 4) if best_f1 else None
        wf = round(sum(worst_f1) / len(worst_f1), 4) if worst_f1 else None
        per_table.append({"table": t, "f1_best": bf, "f1_worst": wf,
                          "delta": round(bf - wf, 4) if bf is not None and wf is not None else None,
                          "schema_loss_worst": avg(worst, "schema_loss"),
                          "population_loss_worst": avg(worst, "population_loss"),
                          "schema_loss_all": avg(rows, "schema_loss"),
                          "population_loss_all": avg(rows, "population_loss")})
    per_table.sort(key=lambda x: -(x["delta"] or 0))
    schema_total = sum(v["schema_loss"] for a in attributions.values() for v in a.values())
    pop_total = sum(v["population_loss"] for a in attributions.values() for v in a.values())
    total = schema_total + pop_total
    share = round(schema_total / total, 4) if total else 0.0
    if total == 0:
        verdict = "nessuna perdita"
    elif share >= 0.6:
        verdict = "schema"
    elif share <= 0.4:
        verdict = "popolamento"
    else:
        verdict = "mista"
    return {**base, "available": True, "best": [run_view(r) for r in best], "worst": [run_view(r) for r in worst],
            "per_table": per_table,
            "attribution": {"schema_share": share, "population_share": round(1 - share, 4) if total else 0.0,
                            "verdict": verdict, "note": "Approssimazione: le colonne gold senza corrispondente "
                                                       "nello schema generato contano come perdita di schema."}}
