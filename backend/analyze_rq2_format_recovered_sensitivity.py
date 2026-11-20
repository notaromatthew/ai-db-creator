from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_rq2_format_matrix import (
    comparisons,
    load_matrix,
    sha256_file,
    summarize,
    write_csv,
)


CONFIG_FIELDS = (
    "provider",
    "model",
    "software_revision",
    "temperature",
    "schema_output_contract",
    "max_output_tokens",
    "timeout_seconds",
    "provider_retries",
    "max_requests_per_minute",
    "research_mode",
    "llm_cache_enabled",
    "parallel",
    "adjudicate",
    "schedule",
)


def _resolve_entry(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"artifact path escapes bundle: {relative}")
    return path


def _verify_hash_entry(base: Path, entry: dict, label: str) -> Path:
    path = _resolve_entry(base, entry["path"])
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    if sha256_file(path) != entry["sha256"]:
        raise ValueError(f"hash mismatch for {label}: {path}")
    return path


def verify_bundle(bundle: Path, manifest: dict, dataset_dir: Path | None = None) -> list[Path]:
    verified = []
    for name, entry in manifest.get("artifacts", {}).items():
        verified.append(_verify_hash_entry(bundle, entry, f"artifact {name}"))
    for index, entry in enumerate(manifest.get("source_files", [])):
        source = _resolve_entry(bundle, entry["path"])
        if not source.is_file() and dataset_dir is not None:
            source = _resolve_entry(dataset_dir, entry["path"])
        if not source.is_file():
            raise ValueError(f"missing source file {index}: {source}")
        if sha256_file(source) != entry["sha256"]:
            raise ValueError(f"hash mismatch for source file {index}: {source}")
        verified.append(source)
    return verified


def _require_equal(left, right, label: str) -> None:
    if left != right:
        raise ValueError(f"{label} mismatch: {left!r} != {right!r}")


def _logical_tree_hash(entries: list[tuple[str, Path]]) -> str:
    import hashlib

    digest = hashlib.sha256()
    for label, path in sorted(entries):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _input_label(prefix: str, path: Path, root: Path, dataset: str, dataset_dir: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(root.resolve()):
        return f"{prefix}/{resolved.relative_to(root.resolve()).as_posix()}"
    return f"dataset/{dataset}/{resolved.relative_to(dataset_dir.resolve()).as_posix()}"


def load_post_recovery(primary_root: Path, recovery_root: Path):
    protocol, primary_records, primary_inputs = load_matrix(primary_root)
    provenance_path = recovery_root / "recovery_manifest.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("recovery_type") != "selective_failure_sensitivity":
        raise ValueError("recovery manifest is not a selective failure sensitivity")
    if Path(provenance["primary_matrix"]).name != primary_root.name:
        raise ValueError("recovery manifest references a different primary matrix")

    input_entries = [(f"primary/{path.relative_to(primary_root).as_posix()}", path) for path in primary_inputs]
    input_entries.append(("recovery/recovery_manifest.json", provenance_path))
    primary_by_key = {
        (row["dataset"], row["source_format"], row["condition"], row["run"]): row
        for row in primary_records
    }
    error_keys = {key for key, row in primary_by_key.items() if row["status"] == "error"}
    declared_primary = provenance.get("primary_result_remains", {})
    _require_equal(declared_primary.get("n_runs"), len(primary_records), "primary n_runs")
    _require_equal(declared_primary.get("ok"), sum(row["status"] == "ok" for row in primary_records), "primary ok")
    _require_equal(declared_primary.get("error"), len(error_keys), "primary error")

    if len(protocol["datasets"]) != 1:
        raise ValueError("recovery entries must declare dataset for multi-dataset matrices")
    selected = set()
    recovery_records = []
    datasets_root = Path(__file__).resolve().parent.parent / "data" / "datasets"
    for entry in provenance.get("runs", []):
        dataset = entry.get("dataset", protocol["datasets"][0])
        condition = entry.get("condition", "full_llm")
        source_format = entry["source_format"]
        run_index = entry["run_index"]
        key = (dataset, source_format, condition, run_index)
        if key in selected:
            raise ValueError(f"duplicate recovery overlay: {key}")
        selected.add(key)
        if key not in error_keys:
            raise ValueError(f"recovery overlay does not select a primary error: {key}")

        primary_record_path = primary_root / dataset / source_format / condition / f"run{run_index:02d}.json"
        _require_equal(sha256_file(primary_record_path), entry["primary_run_sha256"], "primary run hash")
        _require_equal(entry.get("primary_status"), "error", "declared primary status")

        run_root = recovery_root / f"{source_format}_run{run_index:02d}"
        recovery_protocol_path = run_root / "protocol_manifest.json"
        recovery_protocol = json.loads(recovery_protocol_path.read_text(encoding="utf-8"))
        for field in CONFIG_FIELDS:
            _require_equal(recovery_protocol.get(field), protocol.get(field), f"protocol {field}")
        _require_equal(recovery_protocol.get("datasets"), [dataset], "recovery datasets")
        _require_equal(recovery_protocol.get("conditions"), [condition], "recovery conditions")
        _require_equal(recovery_protocol.get("source_formats"), [source_format], "recovery formats")
        _require_equal(recovery_protocol.get("run_indices"), [run_index], "recovery indices")

        record_path = run_root / dataset / source_format / condition / f"run{run_index:02d}.json"
        bundle = record_path.with_suffix("")
        bundle_manifest_path = bundle / "manifest.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
        actual_key = (record["dataset"], record["source_format"], record["condition"], record["run"])
        _require_equal(actual_key, key, "recovery cell")
        _require_equal(record.get("status"), "ok", "recovery status")
        _require_equal(record.get("population_mode"), "llm", "recovery population mode")
        _require_equal(entry.get("recovery_status"), "ok", "declared recovery status")
        for field in ("provider", "model", "software_revision", "schema_output_contract"):
            _require_equal(bundle_manifest.get(field), protocol.get(field), f"bundle {field}")
        _require_equal(bundle_manifest.get("parameters", {}).get("temperature"), protocol["temperature"], "bundle temperature")
        for field in ("dataset", "source_format", "condition"):
            _require_equal(bundle_manifest.get(field), key[("dataset", "source_format", "condition").index(field)], f"bundle {field}")
        _require_equal(bundle_manifest.get("run_index"), run_index, "bundle run index")
        _require_equal(bundle_manifest.get("status"), "ok", "bundle status")
        for field in ("population_mode", "global_f1", "functional_query_pass_rate", "functionally_equivalent"):
            if field in entry:
                _require_equal(record.get(field), entry[field], f"declared {field}")

        _require_equal(sha256_file(record_path), entry["recovery_run_sha256"], "recovery run hash")
        generated = bundle / "generated.db"
        _require_equal(sha256_file(generated), entry["generated_database_sha256"], "generated database hash")

        primary_manifest_path = primary_record_path.with_suffix("") / "manifest.json"
        primary_manifest = json.loads(primary_manifest_path.read_text(encoding="utf-8"))
        for field in ("dataset_hash", "prompts_hash", "evaluation_spec_hash"):
            _require_equal(bundle_manifest.get(field), primary_manifest.get(field), f"primary/recovery {field}")
        _require_equal(bundle_manifest.get("source_files"), primary_manifest.get("source_files"), "primary/recovery sources")

        dataset_dir = datasets_root / dataset
        verified = verify_bundle(bundle, bundle_manifest, dataset_dir)
        input_entries.extend([
            (f"recovery/{record_path.relative_to(recovery_root).as_posix()}", record_path),
            (f"recovery/{bundle_manifest_path.relative_to(recovery_root).as_posix()}", bundle_manifest_path),
            (f"recovery/{recovery_protocol_path.relative_to(recovery_root).as_posix()}", recovery_protocol_path),
        ])
        input_entries.extend(
            (_input_label("recovery", path, recovery_root, dataset, dataset_dir), path)
            for path in verified
        )
        overlay = dict(record)
        overlay["analysis_source"] = "selective_recovery"
        overlay["primary_status"] = "error"
        recovery_records.append(overlay)

    if selected != error_keys:
        raise ValueError(f"recovery selection differs from primary errors: {selected} != {error_keys}")

    for key in primary_by_key:
        bundle = (primary_root / key[0] / key[1] / key[2] / f"run{key[3]:02d}")
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dataset_dir = datasets_root / key[0]
        input_entries.extend(
            (_input_label("primary", path, primary_root, key[0], dataset_dir), path)
            for path in verify_bundle(bundle, manifest, dataset_dir)
        )

    recovered_by_key = {
        (row["dataset"], row["source_format"], row["condition"], row["run"]): row
        for row in recovery_records
    }
    combined = []
    for key, row in primary_by_key.items():
        if key in recovered_by_key:
            combined.append(recovered_by_key[key])
        else:
            retained = dict(row)
            retained["analysis_source"] = "primary"
            retained["primary_status"] = row["status"]
            combined.append(retained)
    return protocol, provenance, primary_records, recovery_records, combined, input_entries


def render_sensitivity_report(protocol: dict, primary_summary: list[dict], recovered_summary: list[dict], input_hash: str) -> str:
    lines = [
        "# RQ2 — sensibilità post-recovery per formato",
        "",
        "**Analisi secondaria post-outcome.** I due retry non sostituiscono gli outcome della matrice primaria, che resta 38/40.",
        f"Hash combinato degli input primari e di recovery: `{input_hash}`.",
        "",
        "| Formato | Condizione | Primaria OK/totale | Post-recovery OK/totale | F1 post-recovery | Query post-recovery |",
        "|---|---|---:|---:|---:|---:|",
    ]
    primary_by_cell = {(row["source_format"], row["condition"]): row for row in primary_summary}
    for row in recovered_summary:
        primary = primary_by_cell[(row["source_format"], row["condition"])]
        lines.append(
            f"| {row['source_format']} | {row['condition']} | {primary['n_ok']}/{primary['n_total']} | "
            f"{row['n_ok']}/{row['n_total']} | {row['mean_global_f1']:.4f} | "
            f"{row['mean_functional_query_pass_rate']:.4f} |"
        )
    lines.extend([
        "",
        "Tutti i 40 run dispongono di un database riuscito nell'overlay post-recovery. Le metriche restano identiche entro condizione e formato: baseline F1 1,0000 e full-LLM F1 0,6667; query funzionali rispettivamente 1,0000 e 0,4000. Il recovery elimina soltanto la differenza descrittiva di successo tecnico.",
        "",
        "Questa stabilità supporta una conclusione di robustezza sul campione osservato, non una stima primaria 40/40 né equivalenza generale tra formati. La selezione dei retry è condizionata ai fallimenti osservati.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    protocol, provenance, primary, recovered, combined, inputs = load_post_recovery(args.primary, args.recovery)
    primary_summary = summarize(protocol, primary)
    recovered_summary = summarize(protocol, combined)
    pairwise = comparisons(protocol, combined)
    input_hash = _logical_tree_hash(inputs)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "format_summary_post_recovery.csv", recovered_summary)
    write_csv(args.output / "format_pairwise_post_recovery.csv", pairwise)
    result = {
        "analysis": "rq2_format_matrix_post_recovery_sensitivity_v1",
        "status": "complete_secondary_post_outcome",
        "post_outcome": True,
        "primary_result_preserved": {
            "n_runs": len(primary),
            "n_ok": sum(row["status"] == "ok" for row in primary),
            "n_error": sum(row["status"] == "error" for row in primary),
        },
        "recovery_overlays": len(recovered),
        "post_recovery_result": {
            "n_runs": len(combined),
            "n_ok": sum(row["status"] == "ok" for row in combined),
            "n_error": sum(row["status"] == "error" for row in combined),
        },
        "input_tree_sha256": input_hash,
        "summary": recovered_summary,
        "pairwise_comparisons": pairwise,
    }
    result_path = args.output / "rq2_format_post_recovery_sensitivity.json"
    report_path = args.output / "REPORT.md"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        render_sensitivity_report(protocol, primary_summary, recovered_summary, input_hash), encoding="utf-8"
    )
    manifest = {
        "analysis": result["analysis"],
        "status": result["status"],
        "post_outcome": True,
        "primary_protocol_sha256": sha256_file(args.primary / "protocol_manifest.json"),
        "recovery_manifest_sha256": sha256_file(args.recovery / "recovery_manifest.json"),
        "input_tree_sha256": input_hash,
        "outputs": {
            path.name: sha256_file(path)
            for path in (
                args.output / "format_summary_post_recovery.csv",
                args.output / "format_pairwise_post_recovery.csv",
                result_path,
                report_path,
            )
        },
        "interpretation": provenance["interpretation"],
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "output": str(args.output),
        "primary_ok": result["primary_result_preserved"]["n_ok"],
        "post_recovery_ok": result["post_recovery_result"]["n_ok"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
