#!/usr/bin/env python3
"""Segnala modifiche alla landing dopo il congelamento della versione di ricerca (task 4.4).

Confronta lo stato corrente con `research-freeze.json` (radice del repo, o percorso passato come
argomento). Non blocca mai il rilascio: esce sempre con 0 e stampa un avviso.

Formato di research-freeze.json:
  {"software_revision": "...", "landing_hash": "..."}
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.core.revision import compute_revision  # noqa: E402

LANDING_DIR = REPO / "frontend" / "src" / "site"


def landing_hash(landing_dir: Path = LANDING_DIR) -> str:
    digest = hashlib.sha256()
    if landing_dir.is_dir():
        for path in sorted(p for p in landing_dir.rglob("*") if p.is_file()):
            digest.update(path.relative_to(landing_dir).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
    return digest.hexdigest()[:16]


def check(freeze_path: Path, landing_dir: Path = LANDING_DIR, revision: str | None = None) -> list[str]:
    """Restituisce l'elenco degli avvisi (vuoto se nessuna differenza o nessun congelamento)."""
    if not freeze_path.exists():
        return []
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    warnings = []
    current_rev = revision if revision is not None else compute_revision()
    if freeze.get("software_revision") and freeze["software_revision"] != current_rev:
        warnings.append(
            f"ATTENZIONE: la revisione del software ({current_rev}) differisce da quella congelata "
            f"({freeze['software_revision']}): i risultati di ricerca non sono piu' riferibili.")
    if freeze.get("landing_hash") and freeze["landing_hash"] != landing_hash(landing_dir):
        warnings.append("Avviso: la landing e' cambiata dopo il congelamento. "
                        "Non altera la revisione del software, quindi il rilascio non e' bloccato.")
    return warnings


def main(argv: list[str]) -> int:
    freeze_path = Path(argv[1]) if len(argv) > 1 else REPO / "research-freeze.json"
    if not freeze_path.exists():
        print(f"{freeze_path.name} non trovato: nessun congelamento da verificare.")
        return 0
    warnings = check(freeze_path)
    print("\n".join(warnings) if warnings else "Nessuna modifica rispetto al congelamento.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
