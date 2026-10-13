"""Dati per la landing (6.4), controllo di congelamento (9.1) e migrazione f6."""
import json
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.services import research_site

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def sample_export(revisions=("abc123",) * 2, finished="2026-10-10T10:00:00"):
    runs = [{"status": "done", "dataset": "university", "condition": "full_llm", "model": "gemini-2.5-flash-lite",
             "temperature": 0.5, "finished_at": finished, "manifest": {"software_revision": rev}} for rev in revisions]
    stat = {"n": 2, "mean": 0.7, "low": 0.6, "high": 0.8}
    summary = [{"dataset": "university", "condition": "full_llm", "model": "gemini-2.5-flash-lite", "temperature": 0.5,
                "n_runs": 2, "f1": stat, "precision": stat, "recall": stat,
                "value_accuracy": {"n": 0, "mean": None, "low": None, "high": None}, "judge_score": stat}]
    return runs, summary


def test_every_published_number_has_version_model_and_date():
    runs, summary = sample_export()
    doc = research_site.build_results(runs, summary)
    assert doc["label"] == "Risultati preliminari" and doc["schema_version"] == 1
    assert {n["metric"] for n in doc["numbers"]} == {"f1", "precision", "recall", "judge_score"}
    for n in doc["numbers"]:
        assert n["software_version"] == "abc123" and n["model"] == "gemini-2.5-flash-lite" and n["date"] == "2026-10-10"
        assert n["ci95"] == [0.6, 0.8] and n["n_runs"] == 2
    assert research_site.validate_results(doc) == []


def test_numbers_without_provenance_are_excluded():
    runs, summary = sample_export(revisions=("a", "b"))  # versioni miste
    doc = research_site.build_results(runs, summary)
    assert doc["numbers"] == [] and len(doc["skipped_without_provenance"]) == 4
    runs, summary = sample_export(finished=None)
    assert research_site.build_results(runs, summary)["numbers"] == []
    bad = {"numbers": [{"value": 0.5, "model": "m", "date": "2026-01-01"}]}
    assert research_site.validate_results(bad)
    assert not research_site.number_is_publishable({"value": float("nan"), "software_version": "a", "model": "m", "date": "2026-01-01"})
    assert not research_site.number_is_publishable({"value": 1, "software_version": "a", "model": "m", "date": "ieri"})


def test_committed_results_json_is_valid():
    path = ROOT / "frontend" / "src" / "site" / "data" / "results.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert research_site.validate_results(doc) == []


def test_export_script_writes_validated_file(tmp_path):
    runs, summary = sample_export()
    source = tmp_path / "export.json"
    source.write_text(json.dumps({"runs": runs, "summary": summary}))
    out = tmp_path / "results.json"
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_site_data.py"), "--from-file", str(source),
                           "--output", str(out)], capture_output=True, text=True, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    assert len(json.loads(out.read_text())["numbers"]) == 4
    assert subprocess.run([sys.executable, str(ROOT / "scripts" / "export_site_data.py"), "--check", "--output", str(out)],
                          cwd=tmp_path).returncode == 0
    broken = json.loads(out.read_text())
    del broken["numbers"][0]["model"]
    out.write_text(json.dumps(broken))
    assert subprocess.run([sys.executable, str(ROOT / "scripts" / "export_site_data.py"), "--check", "--output", str(out)],
                          cwd=tmp_path, capture_output=True).returncode == 1


def run_freeze(tmp_path, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "freeze_check.py"), "--output", str(tmp_path / "f.json"), *args],
                          capture_output=True, text=True, cwd=tmp_path)


def test_freeze_manifest_contents_and_not_ready_without_tests(tmp_path):
    done = run_freeze(tmp_path)
    assert done.returncode == 0, done.stderr
    m = json.loads((tmp_path / "f.json").read_text())
    from app.core.revision import software_revision
    assert m["software_revision"] == software_revision()
    assert set(m["dataset_hashes"]) >= {"university", "library", "hospital"} and all(len(v) == 64 for v in m["dataset_hashes"].values())
    registered = json.loads((ROOT / "docs" / "prompt-hashes.json").read_text())["prompts"]
    assert m["prompt_hashes"] == registered
    assert m["model"]["model"] and m["model"]["provider"] and "metrics" in m
    assert m["checks"]["tests"] == "not_run" and m["ready"] is False and m["problems"] == []


def test_freeze_detects_unregistered_metric_change(tmp_path):
    assert run_freeze(tmp_path).returncode == 0
    m = json.loads((tmp_path / "f.json").read_text())
    first = next(iter(m["metrics"]))
    m["metrics"][first] = "0" * 64  # come se la metrica fosse cambiata dopo la registrazione
    (tmp_path / "f.json").write_text(json.dumps(m))
    bad = run_freeze(tmp_path)
    assert bad.returncode == 1 and "Metriche modificate" in bad.stderr
    assert run_freeze(tmp_path, "--approve-metrics").returncode == 0


def test_freeze_detects_unregistered_prompt_change(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "backend"))
    import freeze_check
    work = tmp_path / "repo"
    (work / "docs").mkdir(parents=True)
    (work / "backend/app/core").mkdir(parents=True)
    (work / "backend/app/core/llm.py").write_text('SCHEMA_PROMPT = "uno"\n')
    (work / "docs/prompt-hashes.json").write_text(json.dumps({"prompts": {}}))
    manifest, problems = freeze_check.build_manifest("passed", None, False, root=work)
    assert problems and "Prompt modificati senza registrazione" in problems[0] and manifest["ready"] is False
    import prompt_hashes
    (work / "docs/prompt-hashes.json").write_text(json.dumps({"prompts": prompt_hashes.collect_prompts(work)}))
    manifest, problems = freeze_check.build_manifest("passed", None, False, root=work)
    assert problems == [] and manifest["ready"] is True
    manifest, problems = freeze_check.build_manifest("failed", None, False, root=work)
    assert problems == ["Test non verdi"] and manifest["ready"] is False


def alembic_cfg(engine):
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["engine"] = engine
    return cfg


def test_f6_is_single_head_and_creates_tables_idempotently(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    cfg = alembic_cfg(engine)
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["g7hardening00007"]
    assert script.get_revision("g7hardening00007").down_revision == "f6research00006"
    assert script.get_revision("f6research00006").down_revision == "e5jobs00005"
    command.upgrade(cfg, "e5jobs00005")
    from app.models.database import Base
    Base.metadata.create_all(engine)  # come al riavvio: tabelle nuove gia' presenti
    command.upgrade(cfg, "head")
    names = set(sa.inspect(engine).get_table_names())
    assert {"research_runs", "study_participants", "study_events", "study_responses"} <= names
    command.downgrade(cfg, "e5jobs00005")
    assert "research_runs" not in sa.inspect(engine).get_table_names()
