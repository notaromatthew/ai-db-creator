"""Consolidate RQ2 numbers from a run_benchmark report tree into JSON.

For each (dataset, condition) this reads the per-run ``run<NN>.json`` records
and the ``{condition}_summary.json`` written by run_benchmark (mean precision/
recall/F1 + Wilson 95% CI + mean adjudication scores), and emits one flat JSON
suitable for building the results tables in the thesis/paper draft.

Usage:
    python aggregate_benchmark.py --reports reports/benchmark
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def mean(vals):
    vals = list(vals)
    return sum(vals) / len(vals) if vals else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/benchmark_aggregates.json"))
    args = parser.parse_args(argv)

    summary_paths = sorted(args.reports.rglob("*_summary.json"))
    if not summary_paths:
        raise SystemExit(f"no *_summary.json found under {args.reports}")

    out = {}
    for sp in summary_paths:
        summary = json.loads(sp.read_text(encoding="utf-8"))
        ds = summary["dataset"]
        cond = summary["condition"]
        key = f"{ds}/{cond}"

        # per-run detail from the {condition}/run<NN>.json sibling directory
        run_dir = sp.parent / cond
        run_records = []
        for runf in sorted(run_dir.glob("run*.json")):
            d = json.loads(runf.read_text(encoding="utf-8"))
            run_records.append({
                "run": d.get("run"),
                "status": d.get("status"),
                "f1": d.get("global_f1"),
                "precision": d.get("global_precision"),
                "recall": d.get("global_recall"),
                "cells": d.get("total_cells"),
                "missing_rows": d.get("missing_rows"),
                "extra_rows": d.get("extra_rows"),
            })

        f1s = [r["f1"] for r in run_records if r["f1"] is not None]

        def adj_dim(attr):
            vals = []
            for runf in sorted(run_dir.glob("run*.json")):
                d = json.loads(runf.read_text(encoding="utf-8"))
                a = d.get("adjudication")
                if a and isinstance(a.get("scores"), dict):
                    v = a["scores"].get(attr)
                    if v is not None:
                        vals.append(v)
            return vals

        out[key] = {
            "dataset": ds,
            "condition": cond,
            "n_runs_total": summary.get("n_runs"),
            "n_runs_f1": len(f1s),
            "per_run_f1": f1s,
            "mean_f1": summary.get("mean_f1"),
            "mean_precision": summary.get("mean_precision"),
            "mean_recall": summary.get("mean_recall"),
            "ci95_f1": summary.get("ci95_f1"),
            "mean_cells": summary.get("mean_cells"),
            "mean_missing_rows": summary.get("mean_missing_rows"),
            "mean_extra_rows": summary.get("mean_extra_rows"),
            "adj_schema_eq": mean(adj_dim("schema_equivalence")),
            "adj_value_acc": mean(adj_dim("value_accuracy")),
            "adj_completeness": mean(adj_dim("completeness")),
            "n_adjudicated": len(adj_dim("schema_equivalence")),
        }

    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())