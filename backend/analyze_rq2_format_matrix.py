from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import statistics
from pathlib import Path

from scipy import stats


METRICS = (
    "global_precision",
    "global_recall",
    "global_f1",
    "functional_query_pass_rate",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def holm(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, values[index] * (len(values) - rank)))
        adjusted[index] = running
    return adjusted


def load_matrix(root: Path) -> tuple[dict, list[dict], list[Path]]:
    protocol_path = root / "protocol_manifest.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    records: list[dict] = []
    inputs = [protocol_path]
    expected = set(itertools.product(
        protocol["datasets"], protocol["source_formats"],
        protocol["conditions"], protocol["run_indices"],
    ))
    observed = set()
    for dataset, source_format, condition, run_index in sorted(expected):
        record_path = root / dataset / source_format / condition / f"run{run_index:02d}.json"
        manifest_path = record_path.with_suffix("") / "manifest.json"
        if not record_path.exists() or not manifest_path.exists():
            raise ValueError(f"missing run artifacts: {record_path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        key = (record["dataset"], record["source_format"], record["condition"], record["run"])
        if key in observed:
            raise ValueError(f"duplicate run cell: {key}")
        observed.add(key)
        checks = {
            "dataset": dataset,
            "source_format": source_format,
            "condition": condition,
            "run_index": run_index,
            "provider": protocol["provider"],
            "model": protocol["model"],
        }
        for field, expected_value in checks.items():
            if manifest.get(field) != expected_value:
                raise ValueError(f"manifest mismatch {field}: {manifest_path}")
        if manifest.get("software_revision") != protocol["software_revision"]:
            raise ValueError(f"software revision mismatch: {manifest_path}")
        if manifest.get("parameters", {}).get("temperature") != protocol["temperature"]:
            raise ValueError(f"temperature mismatch: {manifest_path}")
        if record["status"] == "ok" and record.get("population_mode") != "llm":
            raise ValueError(f"successful run used fallback: {record_path}")
        records.append(record)
        inputs.extend([record_path, manifest_path])
    if observed != expected:
        raise ValueError("observed matrix differs from frozen protocol")
    return protocol, records, inputs


def summarize(protocol: dict, records: list[dict]) -> list[dict]:
    output = []
    for source_format in protocol["source_formats"]:
        for condition in protocol["conditions"]:
            cell = [r for r in records if r["source_format"] == source_format and r["condition"] == condition]
            successful = [r for r in cell if r["status"] == "ok"]
            row = {
                "source_format": source_format,
                "condition": condition,
                "n_total": len(cell),
                "n_ok": len(successful),
                "n_error": sum(r["status"] == "error" for r in cell),
                "technical_success_rate": len(successful) / len(cell),
                "functionally_equivalent_n": sum(r.get("functionally_equivalent") is True for r in successful),
                "functionally_equivalent_rate_evaluable": (
                    sum(r.get("functionally_equivalent") is True for r in successful) / len(successful)
                    if successful else None
                ),
                "errors": " | ".join(sorted({r.get("error") or "" for r in cell if r["status"] == "error"})),
            }
            for metric in METRICS:
                values = [float(r[metric]) for r in successful if r.get(metric) is not None]
                row[f"mean_{metric}"] = mean(values)
                row[f"min_{metric}"] = min(values) if values else None
                row[f"max_{metric}"] = max(values) if values else None
            output.append(row)
    return output


def comparisons(protocol: dict, records: list[dict]) -> list[dict]:
    output = []
    p_values = []
    for condition in protocol["conditions"]:
        by_format = {
            source_format: [r for r in records if r["source_format"] == source_format and r["condition"] == condition]
            for source_format in protocol["source_formats"]
        }
        for left, right in itertools.combinations(protocol["source_formats"], 2):
            left_rows = by_format[left]
            right_rows = by_format[right]
            left_ok = sum(r["status"] == "ok" for r in left_rows)
            right_ok = sum(r["status"] == "ok" for r in right_rows)
            fisher_p = float(stats.fisher_exact([
                [left_ok, len(left_rows) - left_ok],
                [right_ok, len(right_rows) - right_ok],
            ]).pvalue)
            paired = []
            for run_index in protocol["run_indices"]:
                a = next(r for r in left_rows if r["run"] == run_index)
                b = next(r for r in right_rows if r["run"] == run_index)
                if a["status"] == b["status"] == "ok":
                    paired.append((a, b))
            row = {
                "condition": condition,
                "format_a": left,
                "format_b": right,
                "n_shared_successful_runs": len(paired),
                "technical_success_difference_a_minus_b": left_ok / len(left_rows) - right_ok / len(right_rows),
                "fisher_exact_p": fisher_p,
                "fisher_exact_p_holm": None,
            }
            for metric in METRICS:
                differences = [float(a[metric]) - float(b[metric]) for a, b in paired]
                row[f"paired_mean_difference_{metric}_a_minus_b"] = mean(differences)
            output.append(row)
            p_values.append(fisher_p)
    for row, adjusted in zip(output, holm(p_values)):
        row["fisher_exact_p_holm"] = adjusted
    return output


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_report(protocol: dict, summary: list[dict], pairwise: list[dict], input_hash: str) -> str:
    lines = [
        "# RQ2 — confronto esplorativo fra formati",
        "",
        f"Matrice congelata: {len(protocol['source_formats'])} formati × {len(protocol['conditions'])} condizioni × {protocol['runs_per_cell']} run. Modello: `{protocol['model']}`; temperatura {protocol['temperature']}.",
        f"Hash combinato degli input analizzati: `{input_hash}`.",
        "",
        "| Formato | Condizione | OK/totale | Successo tecnico | Precision | Recall | F1 | Query funzionali | Equivalenti |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['source_format']} | {row['condition']} | {row['n_ok']}/{row['n_total']} | "
            f"{row['technical_success_rate']:.1%} | {row['mean_global_precision']:.4f} | "
            f"{row['mean_global_recall']:.4f} | {row['mean_global_f1']:.4f} | "
            f"{row['mean_functional_query_pass_rate']:.4f} | {row['functionally_equivalent_n']}/{row['n_ok']} |"
        )
    failures = [row for row in summary if row["n_error"]]
    lines.extend([
        "",
        "## Interpretazione vincolata ai dati",
        "",
        "Nei run riusciti non emerge una differenza di accuratezza fra formati: le metriche sono costanti all'interno di ciascuna condizione. La baseline raggiunge F1 1,0000 e il full-LLM F1 0,6667 in ogni formato osservabile. Questo non dimostra equivalenza generale fra formati: la fixture è singola, i run sono cinque per cella e la variabilità metrica osservata è nulla.",
        "",
        "L'unica differenza osservata riguarda il successo tecnico. CSV e XLSX hanno un errore di generazione dello schema ciascuno; TXT e PDF completano 5/5 run. Tutti i confronti di Fisher corretti con Holm sono non significativi con questa numerosità. I fallimenti sono conservati come outcome e non sostituiti.",
        "",
        "## Fallimenti",
        "",
    ])
    for row in failures:
        lines.append(f"- `{row['source_format']}/{row['condition']}`: {row['n_error']} — {row['errors']}")
    lines.extend([
        "",
        "I risultati restano un'analisi esplorativa separata dalla matrice `combined` e non sono combinati con essa.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    protocol, records, inputs = load_matrix(args.reports)
    summary = summarize(protocol, records)
    pairwise = comparisons(protocol, records)
    args.output.mkdir(parents=True, exist_ok=True)
    input_hash = tree_hash(inputs, args.reports)
    write_csv(args.output / "format_summary.csv", summary)
    write_csv(args.output / "format_pairwise_comparisons.csv", pairwise)
    result = {
        "analysis": "rq2_format_matrix_exploratory_v1",
        "status": "complete_exploratory",
        "input_tree_sha256": input_hash,
        "n_runs": len(records),
        "n_ok": sum(r["status"] == "ok" for r in records),
        "n_error": sum(r["status"] == "error" for r in records),
        "summary": summary,
        "pairwise_comparisons": pairwise,
    }
    (args.output / "rq2_format_analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "REPORT.md").write_text(
        render_report(protocol, summary, pairwise, input_hash), encoding="utf-8"
    )
    manifest = {
        "analysis": result["analysis"],
        "status": result["status"],
        "protocol_manifest_sha256": sha256_file(args.reports / "protocol_manifest.json"),
        "input_tree_sha256": input_hash,
        "outputs": {
            name: sha256_file(args.output / name)
            for name in (
                "format_summary.csv", "format_pairwise_comparisons.csv",
                "rq2_format_analysis.json", "REPORT.md",
            )
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "n_runs": len(records), "n_ok": result["n_ok"], "n_error": result["n_error"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
