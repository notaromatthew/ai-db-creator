"""Hash di dataset e prompt e manifesto di riproducibilita' dei run di ricerca."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import settings
from app.core.revision import REPO_ROOT, software_revision
from app.utils.research import stable_hash, utc_now

DATASETS_DIR = REPO_ROOT / "data" / "datasets"
PROMPT_HASHES_FILE = REPO_ROOT / "docs" / "prompt-hashes.json"
DATASET_FILES = ("prompt.txt", "gold_schema.json", "ground_truth.db", "column_alias.json")


def list_datasets(root: Path | None = None) -> list[str]:
    root = root or DATASETS_DIR
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "gold_schema.json").exists())


def _dataset_paths(name: str, root: Path | None = None) -> list[Path]:
    base = (root or DATASETS_DIR) / name
    paths = [base / f for f in DATASET_FILES if (base / f).is_file()]
    source = base / "source"
    if source.is_dir():
        paths += sorted(p for p in source.rglob("*") if p.is_file())
    return paths


def dataset_hash(name: str, root: Path | None = None) -> str | None:
    """SHA-256 di prompt, schema gold, ground truth, alias e documenti sorgente (nomi relativi inclusi)."""
    base = (root or DATASETS_DIR) / name
    paths = _dataset_paths(name, root)
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(base).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") if path.suffix in {".txt", ".json", ".csv"}
                      else path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def dataset_source_chars(name: str, root: Path | None = None) -> int:
    source = (root or DATASETS_DIR) / name / "source"
    if not source.is_dir():
        return 0
    return sum(p.stat().st_size for p in source.rglob("*") if p.is_file())


def registered_prompt_hashes(path: Path | None = None) -> dict:
    try:
        return json.loads((path or PROMPT_HASHES_FILE).read_text(encoding="utf-8")).get("prompts", {})
    except (OSError, ValueError):
        return {}


def prompts_hash(path: Path | None = None) -> str:
    return stable_hash(registered_prompt_hashes(path))


def build_manifest(run: dict, extra: dict | None = None) -> dict:
    """Manifesto di un run: tutto cio' che serve per riprodurlo. Nessun segreto, nessun dato personale."""
    manifest = {
        "software_revision": software_revision(),
        "research_mode": bool(settings.research_mode),
        "dataset": run.get("dataset"),
        "dataset_hash": dataset_hash(run["dataset"]) if run.get("dataset") else None,
        "condition": run.get("condition"),
        "provider": run.get("provider"),
        "model": run.get("model"),
        "parameters": {"temperature": run.get("temperature")},
        "prompts_hash": prompts_hash(),
        "run_index": run.get("run_index"),
        "created_at": utc_now().isoformat(),
    }
    if extra:
        manifest.update(extra)
    return manifest
