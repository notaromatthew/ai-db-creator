#!/usr/bin/env python3
"""F1 per tipo di sorgente (pdf, xlsx, csv, txt) da un file di risultati (task 7.3#2).

Formato del file di risultati (JSON): una lista di record, oppure {"results": [...]}.
Ogni record indica la sorgente (`source_type`, oppure `source` con il nome del file: il tipo e' l'estensione)
e il confronto, in uno dei due modi:
  - conteggi: {"source": "fatture.pdf", "tp": 8, "fp": 2, "fn": 1}
  - insiemi:  {"source": "elenco.csv", "expected": [...], "predicted": [...]}
Gli elementi degli insiemi possono essere stringhe, numeri o liste (per esempio [tabella, chiave, colonna, valore]).

Uso:
    python scripts/f1_by_source.py risultati.json [--output f1_per_sorgente.json]

Per ogni tipo si calcolano precisione, richiamo e F1 "micro" (somma dei conteggi di tutti i record del tipo);
`macro_f1` e' la media degli F1 dei tipi.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

KNOWN_TYPES = ("pdf", "xlsx", "csv", "txt")
ALIASES = {"xls": "xlsx", "tsv": "csv", "text": "txt", "sql": "txt"}


def source_type(record: dict) -> str:
    raw = record.get("source_type")
    if not raw:
        name = str(record.get("source") or "")
        raw = name.rsplit(".", 1)[-1] if "." in name else "sconosciuto"
    raw = str(raw).lower().lstrip(".")
    return ALIASES.get(raw, raw)


def _freeze(item):
    return json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)


def counts(record: dict) -> tuple[int, int, int]:
    """(tp, fp, fn) di un record, da conteggi diretti o da insiemi atteso/predetto."""
    if "expected" in record or "predicted" in record:
        expected = {_freeze(i) for i in record.get("expected") or []}
        predicted = {_freeze(i) for i in record.get("predicted") or []}
        tp = len(expected & predicted)
        return tp, len(predicted - expected), len(expected - predicted)
    try:
        return int(record["tp"]), int(record["fp"]), int(record["fn"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Ogni record richiede tp/fp/fn oppure expected/predicted.") from exc


def _scores(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4),
            "recall": round(recall, 4), "f1": round(f1, 4)}


def f1_by_source(records: list[dict]) -> dict:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    documents: dict[str, int] = defaultdict(int)
    for record in records:
        kind = source_type(record)
        tp, fp, fn = counts(record)
        totals[kind][0] += tp
        totals[kind][1] += fp
        totals[kind][2] += fn
        documents[kind] += 1
    by_type = {}
    for kind in sorted(totals, key=lambda k: (k not in KNOWN_TYPES, KNOWN_TYPES.index(k) if k in KNOWN_TYPES else 0, k)):
        by_type[kind] = {**_scores(*totals[kind]), "records": documents[kind]}
    macro = round(sum(v["f1"] for v in by_type.values()) / len(by_type), 4) if by_type else 0.0
    return {"by_source_type": by_type, "macro_f1": macro}


def load_records(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("results", [])
    if not isinstance(data, list):
        raise ValueError("Il file deve contenere una lista di record.")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F1 per tipo di sorgente.")
    parser.add_argument("results", help="File JSON con i risultati")
    parser.add_argument("--output", help="Dove scrivere il riepilogo JSON")
    args = parser.parse_args(argv)
    report = f1_by_source(load_records(args.results))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
