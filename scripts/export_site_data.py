#!/usr/bin/env python3
"""Esporta i dati aggregati dei run in `frontend/src/site/data/results.json` per la landing (task 6.4).

Regola: la landing mostra solo numeri che riportano versione del software, modello e data. I gruppi di run con
versioni miste o senza data restano fuori (elencati in `skipped_without_provenance`).

Uso (dalla radice del repository, con il database dell'app raggiungibile e RESEARCH_MODE non richiesto):
    python scripts/export_site_data.py                       # legge i run dal database
    python scripts/export_site_data.py --from-file run-ricerca.json   # legge un export JSON del pannello ricercatore
    python scripts/export_site_data.py --check               # solo verifica del file esistente (uscita 1 se non valido)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
OUTPUT = ROOT / "frontend" / "src" / "site" / "data" / "results.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-file", type=Path, help="export JSON del pannello ricercatore")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="verifica il file esistente senza riscriverlo")
    args = parser.parse_args(argv)

    from app.services.research_site import build_results, validate_results
    from app.utils.research import atomic_write_json

    if args.check:
        try:
            doc = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"File non leggibile: {exc}", file=sys.stderr)
            return 1
        errors = validate_results(doc)
        for e in errors:
            print(e, file=sys.stderr)
        return 1 if errors else 0

    if args.from_file:
        data = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        from app.services import research_runs
        data = research_runs.export_json(status="done")
    doc = build_results(data.get("runs", []), data.get("summary", []))
    assert not validate_results(doc)
    atomic_write_json(args.output, doc)
    print(f"{len(doc['numbers'])} numeri scritti in {args.output} "
          f"({len(doc['skipped_without_provenance'])} esclusi per provenienza incompleta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
