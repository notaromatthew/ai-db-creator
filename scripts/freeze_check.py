#!/usr/bin/env python3
"""Controllo di congelamento prima della raccolta dati (task 9.1). Non crea tag git.

Verifica:
  - test verdi (solo con --run-tests: pytest del backend e vitest del frontend);
  - nessun prompt modificato senza registrazione (docs/prompt-hashes.json, vedi scripts/prompt_hashes.py);
  - nessuna metrica modificata senza registrazione (hash dei file di valutazione confrontato con quello gia' registrato
    in research-freeze.json; per approvare un cambiamento: --approve-metrics).

Scrive/aggiorna `research-freeze.json` (radice del repository) con: revisione del software (app.core.revision), modello e
versione dalla configurazione, hash dei prompt, hash dei dataset, hash delle metriche, esito dei controlli.

Uso:
    python scripts/freeze_check.py                 # controlla e aggiorna il manifesto (test "not_run")
    python scripts/freeze_check.py --run-tests     # esegue anche i test
    python scripts/freeze_check.py --check         # solo confronto con il manifesto esistente, senza scrivere
    python scripts/freeze_check.py --approve-metrics
Uscita 0 se tutto e' in ordine, 1 altrimenti. Il manifesto e' marcato "ready" solo con test eseguiti e verdi.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
FREEZE_FILE = ROOT / "research-freeze.json"
METRIC_FILES = (
    "backend/app/evaluation/population_evaluation.py",
    "backend/app/evaluation/schema_alignment.py",
    "backend/app/evaluation/llm_adjudication.py",
    "backend/app/services/metrics_service.py",
    "backend/app/services/research_stats.py",
    "backend/run_benchmark.py",
)


def file_hash(relative: str, root: Path = ROOT) -> str | None:
    path = root / relative
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def metrics_hashes(root: Path = ROOT) -> dict:
    return {f: file_hash(f, root) for f in METRIC_FILES}


def prompt_check(root: Path = ROOT) -> dict:
    import prompt_hashes
    current = prompt_hashes.collect_prompts(root)
    try:
        registered = json.loads((root / "docs" / "prompt-hashes.json").read_text(encoding="utf-8")).get("prompts", {})
    except (OSError, ValueError):
        registered = {}
    changed = sorted(k for k in current if registered.get(k) != current[k])
    removed = sorted(k for k in registered if k not in current)
    return {"hashes": current, "unregistered_changes": changed + removed}


def dataset_hashes() -> dict:
    from app.services import research_manifest
    return {name: research_manifest.dataset_hash(name) for name in research_manifest.list_datasets()}


def model_info() -> dict:
    from app.config import settings
    from app.core.llm import get_llm_info
    try:
        info = get_llm_info()
    except Exception:
        info = {}
    return {"provider": info.get("provider", settings.llm_provider), "model": info.get("model"),
            "temperature_default": settings.llm_temperature}


def run_tests() -> str:
    backend = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=ROOT / "backend")
    if backend.returncode != 0:
        return "failed"
    frontend = ROOT / "frontend"
    if (frontend / "node_modules").is_dir():
        if subprocess.run(["npx", "vitest", "run"], cwd=frontend).returncode != 0:
            return "failed"
    return "passed"


def build_manifest(tests: str, previous: dict | None, approve_metrics: bool, root: Path = ROOT) -> tuple[dict, list[str]]:
    from app.core.revision import software_revision
    from app.config import settings
    problems = []
    prompts = prompt_check(root)
    if prompts["unregistered_changes"]:
        problems.append("Prompt modificati senza registrazione: " + ", ".join(prompts["unregistered_changes"])
                        + " (esegui scripts/prompt_hashes.py --write e aggiorna il changelog)")
    metrics = metrics_hashes(root)
    registered = (previous or {}).get("metrics")
    if registered and registered != metrics and not approve_metrics:
        diff = sorted(k for k in metrics if registered.get(k) != metrics[k])
        problems.append("Metriche modificate senza registrazione: " + ", ".join(diff) + " (usa --approve-metrics)")
        metrics = registered
    if tests == "failed":
        problems.append("Test non verdi")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "software_revision": software_revision(),
        "research_mode": bool(settings.research_mode),
        "model": model_info(),
        "prompt_hashes": prompts["hashes"],
        "dataset_hashes": dataset_hashes(),
        "metrics": metrics,
        "checks": {"tests": tests, "prompts_registered": not prompts["unregistered_changes"],
                   "metrics_registered": not any(p.startswith("Metriche") for p in problems)},
        "problems": problems,
    }
    manifest["ready"] = tests == "passed" and not problems
    return manifest, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--check", action="store_true", help="non scrive il file")
    parser.add_argument("--approve-metrics", action="store_true")
    parser.add_argument("--output", type=Path, default=FREEZE_FILE)
    args = parser.parse_args(argv)

    previous = None
    if args.output.exists():
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
        except ValueError:
            previous = None
    tests = run_tests() if args.run_tests else "not_run"
    manifest, problems = build_manifest(tests, previous, args.approve_metrics)
    if previous and args.check:
        for key in ("software_revision", "prompt_hashes", "dataset_hashes"):
            if previous.get(key) != manifest.get(key):
                problems.append(f"{key} diverso dal manifesto congelato")
    if not args.check:
        from app.utils.research import atomic_write_json
        atomic_write_json(args.output, manifest)
        print(f"Manifesto scritto in {args.output} (ready={manifest['ready']})")
    for p in problems:
        print(f"PROBLEMA: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
