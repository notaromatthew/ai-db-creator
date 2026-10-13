"""Dati aggregati per la landing: solo numeri con versione del software, modello e data (task 6.4)."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone

SCHEMA_VERSION = 1
REQUIRED_FIELDS = ("software_version", "model", "date")
METRIC_KEYS = ("f1", "precision", "recall", "value_accuracy", "judge_score")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def number_is_publishable(item: dict) -> bool:
    """Un numero va in pagina solo con valore finito, versione del software, modello e data (YYYY-MM-DD)."""
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return False
    if any(not isinstance(item.get(f), str) or not item[f].strip() for f in REQUIRED_FIELDS):
        return False
    return bool(_DATE.match(item["date"]))


def build_results(runs: list[dict], summary: list[dict], generated_at: datetime | None = None) -> dict:
    """`runs` e `summary` hanno il formato di research_runs.export_json (run con manifest, gruppi con intervalli)."""
    by_group: dict[tuple, list[dict]] = defaultdict(list)
    for run in runs:
        if run.get("status") == "done":
            by_group[(run["dataset"], run["condition"], run["model"], run["temperature"])].append(run)
    numbers, skipped = [], []
    for group in summary:
        key = (group["dataset"], group["condition"], group["model"], group["temperature"])
        members = by_group.get(key, [])
        revisions = {(r.get("manifest") or {}).get("software_revision") for r in members}
        dates = [str(r.get("finished_at") or "")[:10] for r in members if r.get("finished_at")]
        revision = next(iter(revisions)) if len(revisions) == 1 else None
        for metric in METRIC_KEYS:
            stat = group.get(metric) or {}
            if stat.get("mean") is None:
                continue
            item = {
                "id": ".".join(str(x) for x in (*key[:3], f"t{key[3]}", metric)),
                "dataset": group["dataset"], "condition": group["condition"], "metric": metric,
                "temperature": group["temperature"], "value": stat["mean"], "ci95": [stat["low"], stat["high"]],
                "n_runs": stat["n"], "software_version": revision, "model": group["model"],
                "date": max(dates) if dates else None,
            }
            (numbers if number_is_publishable(item) else skipped).append(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "label": "Risultati preliminari",
        "rule": "Ogni numero riporta versione del software, modello e data.",
        "numbers": numbers,
        "skipped_without_provenance": [s["id"] for s in skipped],
    }


def validate_results(doc: dict) -> list[str]:
    """Elenco degli errori di struttura (vuoto = valido)."""
    errors = []
    if not isinstance(doc, dict) or not isinstance(doc.get("numbers"), list):
        return ["manca l'elenco `numbers`"]
    for i, item in enumerate(doc["numbers"]):
        if not number_is_publishable(item):
            errors.append(f"numbers[{i}] senza valore, versione, modello o data validi")
    return errors
