"""Consolidate RQ1 expert-review packages from an existing benchmark run.

Reads the run records produced by ``run_benchmark.py`` (one JSON per
(dataset, condition, run)) and the persisted schema JSON stored in the backend
state database (``projects.schema_json``), then emits an anonymised expert-review
package per the protocol (docs/11, section 8):

- ``schemas/S<NN>.md`` — a printable, condition-blind printout of each schema.
  Only a random code (S01..S30) and the schema are included; dataset, condition
  and run labels are never rendered, so reviewers cannot infer the arm.
- ``mapping.csv`` — researcher-only correspondence S-code -> dataset/condition/run
  (kept separate so blind review can later be unblinded).
- ``ratings_template.csv`` — pre-formatted score sheet (5 dimensions x 0-4).
- ``README.md`` — instructions for assembling the expert package.

Usage:
    python consolidate_rq1_schemas.py \
        --reports reports/benchmark \
        --seed 42 \
        --output reports/rq1_expert_package
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
from pathlib import Path


def _flag_labels(col: dict) -> list[str]:
    labels = []
    if col.get("is_primary_key"):
        labels.append("PK")
    else:
        labels.append("")
    if col.get("is_unique"):
        labels.append("UQ")
    else:
        labels.append("")
    if col.get("is_not_null"):
        labels.append("NN")
    else:
        labels.append("")
    if col.get("is_foreign_key"):
        labels.append(
            f"FK->{col.get('foreign_key_table')}.{col.get('foreign_key_column')}"
        )
    else:
        labels.append("")
    return labels


def _render_column_lines(col: dict) -> list[str]:
    flags = _flag_labels(col)
    non_empty = [f for f in flags if f]
    suffix = f"  [{', '.join(non_empty)}]" if non_empty else ""
    line = f"  - {col['name']} ({col['data_type']}){suffix}"
    return [line]


def _render_schema(schema: dict) -> str:
    lines = []
    if schema.get("description"):
        lines.append(schema["description"].strip())
        lines.append("")
    for table in schema["tables"]:
        lines.append(f"TABLE {table['name']}")
        for col in table["columns"]:
            lines.extend(_render_column_lines(col))
        lines.append("")
    if schema.get("relationships"):
        lines.append("RELATIONSHIPS")
        for rel in schema["relationships"]:
            lines.append(
                f"  - {rel['from_table']}.{rel['from_column']} "
                f"[{rel.get('type', '')}] {rel['to_table']}.{rel['to_column']}"
            )
    return "\n".join(lines)


def collect_runs(reports_dir: Path) -> list[dict]:
    """Return a list of run records loaded from the benchmark report tree."""
    runs = []
    for path in sorted(reports_dir.rglob("run*.json")):
        runs.append(json.loads(path.read_text(encoding="utf-8")))
    return runs


def load_schemas(runs: list[dict], db_path: Path) -> dict[str, str]:
    """Return {project_id: rendered-markdown-schema} for every run project."""
    conn = sqlite3.connect(str(db_path))
    out: dict[str, str] = {}
    for r in runs:
        pid = r.get("project_id")
        if not pid:
            continue
        row = conn.execute(
            "SELECT schema_json FROM projects WHERE id = ?", (pid,)
        ).fetchone()
        if not row or not row[0]:
            raise ValueError(f"missing schema_json for project {pid}")
        schema = json.loads(row[0])
        out[pid] = _render_schema(schema)
    conn.close()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, required=True,
                        help="Path to a run_benchmark output tree (eg reports/benchmark).")
    parser.add_argument("--db", type=Path, default=Path("app.db"),
                        help="Backend state database holding schema_json.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for the blind code assignment (set for reproducibility).")
    parser.add_argument("--output", type=Path, default=Path("reports/rq1_expert_package"),
                        help="Where to write the expert package.")
    args = parser.parse_args(argv)

    runs = collect_runs(args.reports)
    if not runs:
        raise SystemExit(f"no run files found under {args.reports}")
    schemas = load_schemas(runs, args.db)

    rng = random.Random(args.seed)
    codes = list(range(1, len(runs) + 1))
    rng.shuffle(codes)

    out_schemas = args.output / "schemas"
    out_schemas.mkdir(parents=True, exist_ok=True)

    mapping: list[tuple[str, str, str, str]] = []
    for run, code in zip(runs, codes):
        name = f"S{code:02d}"
        path = out_schemas / f"{name}.md"
        path.write_text(
            f"# Schema {name}\n\n"
            f"*Anonymous expert review copy. Do not record any identifying "
            f"information on this sheet.*\n\n"
            f"---\n\n"
            f"{schemas[run['project_id']]}\n",
            encoding="utf-8",
        )
        mapping.append((
            name,
            run["dataset"],
            run["condition"],
            f"run{run['run']}",
        ))

    with (args.output / "mapping.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "dataset", "condition", "run"])
        w.writerows(mapping)

    with (args.output / "ratings_template.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "d1_3nf", "d2_naming", "d3_constraints",
                    "d4_relationships", "d5_domain", "comment"])
        for m in mapping:
            w.writerow([m[0], "", "", "", "", "", ""])

    (args.output / "README.md").write_text(
        "# RQ1 expert-review package\n\n"
        "This directory is generated by `backend/consolidate_rq1_schemas.py` "
        "from the existing `reports/benchmark` run.\n\n"
        "- `schemas/S*.md` — 30 condition-blind schema printouts (one per run).\n"
        "- `ratings_template.csv` — score sheet: dimensions D1..D5 (0-4 Likert) "
        "plus an optional free-text comment.\n"
        "- `mapping.csv` — researcher-only key linking each code to "
        "dataset/condition/run. Keep separate until scoring is complete.\n\n"
        "Distribution (protocol section 8): give experts the `schemas/` files, "
        "the blank score sheet and this protocol; give them random independent "
        "orderings. Never reveal `mapping.csv` before scoring is closed.\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "output": str(args.output.resolve()),
        "n_schemas": len(mapping),
        "seed": args.seed,
        "distinct_conditions": sorted({m[2] for m in mapping}),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())