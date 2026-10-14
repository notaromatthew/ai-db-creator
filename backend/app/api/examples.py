"""Esempi gia' analizzati: schema, richiesta, documenti e dati di tre dataset, in sola lettura e senza login."""
import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from app.utils.exceptions import AppException

router = APIRouter(prefix="/api")

EXAMPLE_NAMES = ("library", "university", "hospital")
PREVIEW_ROWS = 20
CACHE = "public, max-age=300"


def _datasets_dir() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "example_datasets", here.parents[3] / "data" / "datasets"):
        if candidate.is_dir():
            return candidate
    return here.parents[2] / "example_datasets"


def _example_dir(name: str) -> Path:
    if name not in EXAMPLE_NAMES:
        raise AppException(detail="Esempio non trovato", status_code=404)
    path = _datasets_dir() / name
    if not path.is_dir():
        raise AppException(detail="Esempio non trovato", status_code=404)
    return path


def _texts() -> dict:
    try:
        return json.loads((_datasets_dir() / "examples.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _schema(path: Path) -> dict:
    return json.loads((path / "gold_schema.json").read_text(encoding="utf-8"))


def _summary(name: str, path: Path, texts: dict) -> dict:
    schema = _schema(path)
    meta = texts.get(name, {})
    return {
        "name": name,
        "title": meta.get("title", name),
        "subtitle": meta.get("subtitle", ""),
        "icon": meta.get("icon", "database"),
        "tables": len(schema.get("tables", [])),
        "relationships": len(schema.get("relationships", [])),
    }


def _sources(path: Path) -> list[dict]:
    source = path / "source"
    if not source.is_dir():
        return []
    return [{"name": f.name, "size": f.stat().st_size, "kind": f.suffix.lstrip(".").lower()}
            for f in sorted(source.iterdir()) if f.is_file()]


def _preview(path: Path, table_names: list[str]) -> list[dict]:
    db = path / "ground_truth.db"
    if not db.is_file():
        return []
    out = []
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for table in table_names:
            cur = conn.execute(f'SELECT * FROM "{table}" LIMIT {PREVIEW_ROWS}')
            columns = [c[0] for c in cur.description]
            total = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            out.append({"table": table, "columns": columns, "rows": [list(r) for r in cur.fetchall()], "total": total})
    finally:
        conn.close()
    return out


@router.get("/examples")
def list_examples(response: Response):
    response.headers["Cache-Control"] = CACHE
    texts = _texts()
    return {"examples": [_summary(n, _example_dir(n), texts) for n in EXAMPLE_NAMES if (_datasets_dir() / n).is_dir()]}


@router.get("/examples/{name}")
def get_example(name: str, response: Response):
    path = _example_dir(name)
    response.headers["Cache-Control"] = CACHE
    texts = _texts().get(name, {})
    schema = _schema(path)
    prompt_file = path / "prompt.txt"
    return {
        **_summary(name, path, _texts()),
        "intro": texts.get("intro", []),
        "choices": texts.get("choices", []),
        "notes": texts.get("notes", []),
        "prompt": prompt_file.read_text(encoding="utf-8").strip() if prompt_file.is_file() else "",
        "schema": schema,
        "sources": _sources(path),
        "data": _preview(path, [t["name"] for t in schema.get("tables", [])]),
    }


@router.get("/examples/{name}/files/{filename}")
def download_example_file(name: str, filename: str):
    path = _example_dir(name)
    match = next((f for f in _sources(path) if f["name"] == filename), None)
    if match is None:
        raise AppException(detail="File non trovato", status_code=404)
    return FileResponse(path / "source" / match["name"], filename=match["name"], headers={"Cache-Control": CACHE})
