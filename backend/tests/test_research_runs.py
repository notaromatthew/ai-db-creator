"""Pagine del ricercatore: run, riepilogo con intervalli, lancio con stima, coda, esportazione e diagnosi (6.x, 7.1)."""
import csv
import io
import json

import pytest

from app.config import settings
from app.core.auth import get_current_user
from app.main import app
from app.models.database import ResearchRun, get_session, init_db
from app.services import research_runs


def as_user(roles, sub="ricercatore"):
    app.dependency_overrides[get_current_user] = lambda: {"sub": sub, "username": sub, "roles": roles, "email_verified": True}


def per_table(f1_a, f1_b):
    def t(f1):
        return {"exact": int(f1 * 10), "type_consistent": 0, "null_in_source": 10 - int(f1 * 10), "wrong_value": 0,
                "fk_violations": 0, "type_mismatch": 0, "missing_rows": 0, "extra_rows": 0, "total_cells": 10,
                "precision": f1, "recall": f1, "f1": f1}
    return {"studenti": t(f1_a), "corsi": t(f1_b)}


def fake_executor(job):
    base = 0.9 if job["run_index"] % 2 else 0.5
    alignment = None
    if job["condition"] == "full_llm":
        alignment = {"tables": {"studenti": "student"}, "columns": {"studenti": {"id": "id"}, "corsi": {}},
                     "unmatched_tables": ["corsi"] if base < 0.6 else [], "unmatched_columns": {}}
    return {"precision": base, "recall": base, "f1": base, "per_table": per_table(base, base - 0.2 if base < 0.6 else base),
            "judge_score": base + 0.05, "tokens_in": 1000, "tokens_out": 500, "latency_s": 2.0 + job["run_index"],
            "alignment": alignment, "schema": {"tables": [{"name": "student"}]}, "executor": "simulato"}


@pytest.fixture()
def research(client):
    c, _ = client
    as_user(["aidb-researcher"])
    research_runs.set_executor(fake_executor)
    yield c
    research_runs.set_executor(None)
    research_runs.wait_idle(10)


def launch(c, **over):
    body = {"datasets": ["university"], "conditions": ["full_llm"], "model": "gemini-2.5-flash-lite",
            "temperatures": [0.5], "runs": 4, "confirm_cost": True, **over}
    r = c.post("/api/research/batches", json=body)
    research_runs.wait_idle(20)
    return r


def test_off_returns_404_and_non_researchers_403(client):
    c, _ = client
    as_user(["aidb-researcher"])
    settings.research_mode = False
    try:
        assert c.get("/api/research/runs").status_code == 404
        assert c.get("/api/study/admin/status").status_code == 404
    finally:
        settings.research_mode = True
    as_user([])
    assert c.get("/api/research/runs").status_code == 403
    assert c.post("/api/research/batches", json={}).status_code == 403
    as_user(["aidb-admin"])
    assert c.get("/api/research/runs").status_code == 200


def test_estimate_before_launch_and_cost_confirmation(research):
    c = research
    body = {"datasets": ["university", "library"], "conditions": ["full_llm", "baseline"],
            "model": "gemini-2.5-flash-lite", "temperatures": [0.0, 0.5], "runs": 3}
    est = c.post("/api/research/estimate", json=body).json()
    assert est["runs"] == 24 and est["cost_usd"] > 0 and est["approximate"] and est["over_cap"] is False
    # senza conferma del costo non parte nulla
    assert c.post("/api/research/batches", json=body).status_code == 422
    assert c.get("/api/research/runs").json()["runs"] == []
    assert c.post("/api/research/estimate", json={**body, "datasets": ["inventato"]}).status_code == 422
    assert c.post("/api/research/estimate", json={**body, "temperatures": [3]}).status_code == 422
    assert c.post("/api/research/estimate", json={**body, "runs": 20, "temperatures": [0.1, 0.2, 0.3]}).status_code == 422


def test_cost_cap_blocks_launch(research, monkeypatch):
    monkeypatch.setenv("RESEARCH_COST_CAP_USD", "0.0001")
    r = launch(research, confirm_cost=True)
    assert r.status_code == 422 and "tetto" in r.json()["detail"]


def test_batch_runs_through_queue_with_simulated_llm(research):
    c = research
    r = launch(c)
    assert r.status_code == 202 and r.json()["runs"] == 4
    runs = c.get("/api/research/runs").json()["runs"]
    assert len(runs) == 4 and {x["status"] for x in runs} == {"done"}
    detail = c.get(f"/api/research/runs/{runs[0]['id']}").json()
    assert detail["manifest"]["software_revision"] and detail["manifest"]["dataset_hash"]
    assert detail["manifest"]["research_mode"] is True and detail["manifest"]["parameters"] == {"temperature": 0.5}
    assert detail["schema"] == {"tables": [{"name": "student"}]} and set(detail["per_table"]) == {"studenti", "corsi"}
    assert detail["cost_usd"] == pytest.approx((1000 * 0.10 + 500 * 0.40) / 1e6) and detail["latency_s"] >= 2
    assert detail["value_accuracy"] is not None
    assert c.get("/api/research/runs/nonesiste").status_code == 404


def test_filters_by_dataset_condition_model_temperature(research):
    c = research
    launch(c, runs=1)
    launch(c, runs=1, datasets=["library"], conditions=["baseline"], temperatures=[0.0], model="gemini-2.5-flash")
    assert len(c.get("/api/research/runs").json()["runs"]) == 2
    only = c.get("/api/research/runs?dataset=library&condition=baseline&model=gemini-2.5-flash&temperature=0").json()["runs"]
    assert len(only) == 1 and only[0]["dataset"] == "library"
    assert c.get("/api/research/runs?temperature=0.5").json()["runs"][0]["dataset"] == "university"
    assert c.get("/api/research/runs?model=nessuno").json()["runs"] == []
    opts = c.get("/api/research/meta").json()["filters"]
    assert opts["datasets"] == ["library", "university"] and opts["temperatures"] == [0.0, 0.5]


def test_summary_has_bootstrap_intervals_for_all_metrics(research):
    c = research
    launch(c, runs=6)
    group = c.get("/api/research/summary").json()["groups"][0]
    assert group["n_runs"] == 6
    for metric in ("f1", "precision", "recall", "value_accuracy", "judge_score"):
        s = group[metric]
        assert s["low"] <= s["mean"] <= s["high"] and s["n"] == 6
    assert group["f1"]["mean"] == pytest.approx(0.7) and group["f1"]["low"] < 0.7 < group["f1"]["high"]
    assert group["cost_usd_mean"] > 0 and group["latency_s_mean"] > 0
    # deterministico: stesso insieme, stessi intervalli
    assert c.get("/api/research/summary").json()["groups"][0]["f1"] == group["f1"]


def test_bootstrap_edge_cases():
    from app.services.research_stats import bootstrap_ci
    assert bootstrap_ci([]) == {"n": 0, "mean": None, "low": None, "high": None}
    assert bootstrap_ci([0.4, None]) == {"n": 1, "mean": 0.4, "low": 0.4, "high": 0.4}


def test_queue_cancel_queued_and_running(research):
    c = research
    release = __import__("threading").Event()
    started = __import__("threading").Event()

    def slow(job):
        started.set()
        release.wait(10)
        return fake_executor(job)

    research_runs.set_executor(slow)
    r = c.post("/api/research/batches", json={"datasets": ["university"], "conditions": ["baseline"],
                                               "model": "gemini-2.5-flash-lite", "temperatures": [0.1], "runs": 3,
                                               "confirm_cost": True})
    assert r.status_code == 202
    assert started.wait(10)
    queue = c.get("/api/research/queue").json()
    assert queue["running"] == 1 and queue["queued"] == 2
    queued = next(x for x in queue["active"] if x["status"] == "queued")
    running = next(x for x in queue["active"] if x["status"] == "running")
    assert c.post(f"/api/research/runs/{queued['id']}/cancel").json() == {"status": "cancelled"}
    assert c.post(f"/api/research/runs/{running['id']}/cancel").json() == {"status": "cancelling"}
    release.set()
    research_runs.wait_idle(20)
    runs = {x["id"]: x for x in c.get("/api/research/runs").json()["runs"]}
    assert runs[queued["id"]]["status"] == "cancelled" and runs[running["id"]]["status"] == "cancelled"
    assert runs[running["id"]]["f1"] is None
    assert sorted(x["status"] for x in runs.values()) == ["cancelled", "cancelled", "done"]
    assert c.post(f"/api/research/runs/{queued['id']}/cancel").status_code == 409
    assert c.post("/api/research/runs/nonesiste/cancel").status_code == 404


def test_failed_executor_marks_run_failed_without_leaking(research):
    def boom(job):
        raise RuntimeError("chiave segreta abc")
    research_runs.set_executor(boom)
    launch(research, runs=1)
    run = research.get("/api/research/runs").json()["runs"][0]
    assert run["status"] == "failed" and "RuntimeError" in run["error"]


def test_export_csv_and_json(research):
    c = research
    launch(c, runs=2)
    r = c.get("/api/research/export?format=csv")
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 2 and rows[0]["model"] == "gemini-2.5-flash-lite" and rows[0]["software_revision"]
    assert float(rows[0]["f1"]) in (0.9, 0.5)
    wrapped = c.get("/api/research/export?format=json&wrap=1").json()
    doc = json.loads(wrapped["content"])
    assert len(doc["runs"]) == 2 and doc["runs"][0]["manifest"]["prompts_hash"] and doc["summary"]
    assert c.get("/api/research/export?format=xml").status_code == 422


def test_diagnosis_best_worst_and_attribution(research):
    c = research
    launch(c, runs=4)
    d = c.get("/api/research/diagnosis?dataset=university&condition=full_llm&temperature=0.5").json()
    assert d["available"] and d["n_runs"] == 4
    assert all(x["f1"] == 0.9 for x in d["best"]) and all(x["f1"] == 0.5 for x in d["worst"])
    corsi = next(t for t in d["per_table"] if t["table"] == "corsi")
    # nei run peggiori la tabella `corsi` non ha corrispondente nello schema generato: perdita di schema
    assert corsi["schema_loss_worst"] > 0 and corsi["population_loss_worst"] == 0 and corsi["delta"] > 0
    studenti = next(t for t in d["per_table"] if t["table"] == "studenti")
    assert studenti["schema_loss_worst"] == 0 and studenti["population_loss_worst"] == pytest.approx(0.5)
    assert 0 < d["attribution"]["schema_share"] < 1 and d["attribution"]["verdict"] in ("schema", "popolamento", "mista")
    assert c.get("/api/research/diagnosis?temperature=0.1").json()["available"] is False


def test_attribute_loss_baseline_is_all_population():
    out = research_runs.attribute_loss(per_table(0.6, 0.8), None)
    assert out["studenti"]["schema_loss"] == 0 and out["studenti"]["population_loss"] == pytest.approx(0.4)


def test_attribute_loss_missing_columns_share():
    align = {"columns": {"t": {"a": "a"}}, "unmatched_columns": {"t": ["b", "c", "d"]}, "unmatched_tables": []}
    out = research_runs.attribute_loss({"t": {"f1": 0.5}}, align)
    assert out["t"]["schema_loss"] == 0.5 and out["t"]["population_loss"] == 0.0


def test_value_accuracy_from_counts():
    assert research_runs.value_accuracy_from(per_table(0.8, 0.8)) == pytest.approx(0.8)
    assert research_runs.value_accuracy_from(None) is None


def test_import_reports_and_path_guard(research, tmp_path):
    c = research
    folder = tmp_path / "reports" / "b" / "university" / "full_llm"
    folder.mkdir(parents=True)
    (folder / "run01.json").write_text(json.dumps({
        "dataset": "university", "condition": "full_llm", "run": 1, "status": "ok", "temperature": 0.5,
        "global_precision": 0.7, "global_recall": 0.6, "global_f1": 0.65, "model": "gemini-2.5-flash-lite",
        "adjudication": {"scores": {"value_accuracy": 80}}}))
    assert c.post("/api/research/import", json={"path": "b"}).json() == {"imported": 1}
    assert c.post("/api/research/import", json={"path": "b"}).json() == {"imported": 0}
    assert c.post("/api/research/import", json={"path": "../.."}).status_code == 422
    run = c.get("/api/research/runs?temperature=0.5").json()["runs"][0]
    assert run["f1"] == 0.65 and run["judge_score"] == 0.8


def test_stale_running_runs_are_failed(research):
    from datetime import timedelta
    from app.core.acl import utcnow_naive
    session = get_session(init_db())
    session.add(ResearchRun(dataset="university", condition="full_llm", model="m", temperature=0.5, status="running",
                            started_at=utcnow_naive() - timedelta(hours=3)))
    session.commit()
    session.close()
    assert research.get("/api/research/queue").json()["running"] == 0
    assert research.get("/api/research/runs?status=failed").json()["runs"][0]["error"].startswith("Interrotto")


def test_real_executor_counts_tokens_and_restores_state(monkeypatch, tmp_path):
    """Percorso reale con un BenchmarkRunner simulato: nessuna chiamata a LLM."""
    import run_benchmark
    from app.config import settings as s
    from app.core import llm

    class FakeRunner:
        def __init__(self, *a, **k):
            self.schema_svc = type("S", (), {"get_schema": lambda self, pid: type("X", (), {"model_dump": lambda self: {"tables": []}})()})()

        async def _run_one(self, dataset, condition, run_index):
            llm._log_usage(type("R", (), {"usage_metadata": {"input_tokens": 120, "output_tokens": 30}})())
            return {"status": "ok", "global_precision": 0.5, "global_recall": 0.5, "global_f1": 0.5, "alignment": None,
                    "adjudication": {"scores": {"value_accuracy": 70}}}

    monkeypatch.setattr(run_benchmark, "BenchmarkRunner", FakeRunner)
    original = llm._log_usage
    before = s.vertex_model
    out = research_runs.real_executor({"dataset": "university", "condition": "baseline", "model": "altro-modello",
                                       "provider": "vertex", "temperature": 0.5, "run_index": 1})
    assert out["tokens_in"] == 120 and out["tokens_out"] == 30 and out["judge_score"] == 0.7 and out["f1"] == 0.5
    assert llm._log_usage is original and s.vertex_model == before
