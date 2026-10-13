"""Revisione del software ai fini della riproducibilita' (task 4.4).

La revisione dipende solo da backend (app/), prompt e codice dell'applicazione frontend.
La landing (frontend/src/site), i test e la documentazione sono esclusi: cambiare un testo
della landing non deve alterare l'identita' del software con cui si producono i risultati.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_APP.parents[1]

_BACKEND_SUFFIXES = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".j2", ".prompt"}
_FRONTEND_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}
_SKIP_DIRS = {"__pycache__", "node_modules", "tests", "test", "docs", "site", ".git", "dist"}


def _is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or ".test." in name or ".spec." in name


def _walk(root: Path, suffixes: set[str]):
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in _SKIP_DIRS for part in rel_parts[:-1]) or _is_test_file(path):
            continue
        yield path


def tracked_files(backend_app: Path = BACKEND_APP, frontend_src: Path | None = None) -> list[tuple[str, Path]]:
    """Elenco (etichetta, percorso) dei file che concorrono alla revisione."""
    if frontend_src is None:
        frontend_src = REPO_ROOT / "frontend" / "src"
    files = [(f"backend/{p.relative_to(backend_app).as_posix()}", p) for p in _walk(backend_app, _BACKEND_SUFFIXES)]
    files += [(f"frontend/{p.relative_to(frontend_src).as_posix()}", p) for p in _walk(frontend_src, _FRONTEND_SUFFIXES)]
    return files


def compute_revision(backend_app: Path = BACKEND_APP, frontend_src: Path | None = None) -> str:
    digest = hashlib.sha256()
    for label, path in tracked_files(backend_app, frontend_src):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


@lru_cache(maxsize=1)
def _computed() -> str:
    return compute_revision()


def software_revision() -> str:
    """Valore esplicito SOFTWARE_REVISION (impostato in build) oppure hash calcolato."""
    return os.getenv("SOFTWARE_REVISION") or _computed()


def __getattr__(name: str):
    if name == "SOFTWARE_REVISION":
        return software_revision()
    raise AttributeError(name)
