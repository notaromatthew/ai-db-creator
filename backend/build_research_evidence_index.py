from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(rb"sk-or-v1-[A-Za-z0-9_-]+"),
    re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
)
FORBIDDEN_PATH_PARTS = ("private_mapping", "coordinator_private_mapping")


@dataclass(frozen=True)
class EvidenceSpec:
    evidence_id: str
    rq: str
    classification: str
    anchor: str
    files: tuple[str, ...]
    internal_outputs: tuple[tuple[str, str], ...] = ()


EVIDENCE_SPECS = (
    EvidenceSpec(
        "rq1_student_panel", "RQ1", "observed_primary_panel",
        "backend/reports/rq1_analysis/manifest.json",
        (
            "backend/reports/rq1_analysis/manifest.json",
            "backend/reports/rq1_analysis/REPORT.md",
            "backend/reports/rq1_analysis/descriptive_summary.csv",
            "backend/reports/rq1_analysis/agreement.csv",
            "backend/reports/rq1_analysis/condition_comparison.csv",
        ),
    ),
    EvidenceSpec(
        "rq1_expert_replication", "RQ1", "observed_secondary_independent_panel",
        "backend/reports/rq1_expert_replication/manifest.json",
        (
            "backend/reports/rq1_expert_replication/manifest.json",
            "backend/reports/rq1_expert_replication/REPORT.md",
            "backend/reports/rq1_expert_replication/descriptive_summary.csv",
            "backend/reports/rq1_expert_replication/agreement.csv",
            "backend/reports/rq1_expert_replication/condition_comparison.csv",
        ),
    ),
    EvidenceSpec(
        "rq2_gold_standard_consensus_v2", "RQ2", "expert_consensus_current_gold_standard",
        "backend/reports/gold_standard_consensus_20261121/post_amendment_manifest.json",
        (
            "backend/reports/gold_standard_consensus_20261121/post_amendment_manifest.json",
            "backend/reports/gold_standard_consensus_20261121/consensus_decisions.json",
            "docs/26-gold-standard-consensus-amendment-2026-11-21.md",
        ),
    ),
    EvidenceSpec(
        "rq2_v2_primary_matrix", "RQ2", "primary_current_exploratory_matrix",
        "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/execution_complete.json",
        (
            "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/execution_complete.json",
            "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/protocol_manifest.json",
            "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/REPORT.md",
            "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/aggregates.json",
        ),
    ),
    EvidenceSpec(
        "rq2_v2_analysis", "RQ2", "primary_current_exploratory_analysis",
        "backend/reports/rq2_v2_analysis_20261121/manifest.json",
        (
            "backend/reports/rq2_v2_analysis_20261121/manifest.json",
            "backend/reports/rq2_v2_analysis_20261121/rq2_v2_analysis.json",
            "backend/reports/rq2_v2_analysis_20261121/rq2_v2_condition_comparisons.csv",
        ),
        (("backend/reports/rq2_v2_analysis_20261121/manifest.json", "outputs"),),
    ),
    EvidenceSpec(
        "rq2_structured_matrix", "RQ2", "historical_v1_complete_exploratory_matrix",
        "backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/execution_complete.json",
        (
            "backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/execution_complete.json",
            "backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/protocol_manifest.json",
            "backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/execution_day1_20261107.json",
            "backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/execution_day2_20261108.json",
        ),
    ),
    EvidenceSpec(
        "rq2_human_adjudication", "RQ2", "historical_v1_observed_blinded_consensus",
        "backend/reports/rq2_adjudication_completed/final_manifest.json",
        (
            "backend/reports/rq2_adjudication_completed/final_manifest.json",
            "backend/reports/rq2_adjudication_completed/REPORT.md",
            "backend/reports/rq2_adjudication_completed/final_adjudication_ledger.csv",
            "backend/reports/rq2_adjudication_completed/final_adjudication_summary.json",
        ),
        (("backend/reports/rq2_adjudication_completed/final_manifest.json", "outputs"),),
    ),
    EvidenceSpec(
        "rq2_final_analysis", "RQ2", "historical_v1_complete_exploratory_analysis",
        "backend/reports/rq2_final_analysis/manifest.json",
        (
            "backend/reports/rq2_final_analysis/manifest.json",
            "backend/reports/rq2_final_analysis/REPORT.md",
            "backend/reports/rq2_final_analysis/rq2_final_analysis.json",
            "backend/reports/rq2_final_analysis/rq2_condition_comparisons.csv",
        ),
        (("backend/reports/rq2_final_analysis/manifest.json", "outputs"),),
    ),
    EvidenceSpec(
        "rq2_format_primary", "RQ2", "primary_exploratory_format_matrix_38_of_40",
        "backend/reports/rq2_format_analysis/manifest.json",
        (
            "backend/reports/benchmark_format_equivalence_google_gemini35flashlite_20261120/protocol_manifest.json",
            "backend/reports/rq2_format_analysis/manifest.json",
            "backend/reports/rq2_format_analysis/REPORT.md",
            "backend/reports/rq2_format_analysis/format_summary.csv",
            "backend/reports/rq2_format_analysis/format_pairwise_comparisons.csv",
            "backend/reports/rq2_format_analysis/rq2_format_analysis.json",
        ),
        (("backend/reports/rq2_format_analysis/manifest.json", "outputs"),),
    ),
    EvidenceSpec(
        "rq2_format_post_recovery", "RQ2", "secondary_post_outcome_sensitivity_40_of_40",
        "backend/reports/rq2_format_post_recovery_sensitivity/manifest.json",
        (
            "backend/reports/benchmark_format_equivalence_google_gemini35flashlite_selective_recovery_20261120/recovery_manifest.json",
            "backend/reports/rq2_format_post_recovery_sensitivity/manifest.json",
            "backend/reports/rq2_format_post_recovery_sensitivity/REPORT.md",
            "backend/reports/rq2_format_post_recovery_sensitivity/format_summary_post_recovery.csv",
            "backend/reports/rq2_format_post_recovery_sensitivity/format_pairwise_post_recovery.csv",
            "backend/reports/rq2_format_post_recovery_sensitivity/rq2_format_post_recovery_sensitivity.json",
        ),
        (("backend/reports/rq2_format_post_recovery_sensitivity/manifest.json", "outputs"),),
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _safe_path(repo_root: Path, relative: str) -> Path:
    if any(part in relative.lower() for part in FORBIDDEN_PATH_PARTS):
        raise ValueError(f"private artifact cannot enter evidence index: {relative}")
    path = (repo_root / relative).resolve()
    if not path.is_relative_to(repo_root.resolve()):
        raise ValueError(f"path escapes repository: {relative}")
    if not path.is_file():
        raise ValueError(f"missing evidence artifact: {relative}")
    return path


def _scan_for_secrets(path: Path) -> None:
    data = path.read_bytes()
    if any(pattern.search(data) for pattern in SECRET_PATTERNS):
        raise ValueError(f"secret-like value found in evidence artifact: {path}")


def _lookup(payload: dict, dotted: str):
    value = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _revision_metadata(evidence_id: str, anchor: dict, repo_root: Path) -> dict:
    if evidence_id in {"rq1_student_panel", "rq1_expert_replication"}:
        return {"software_revision": anchor.get("software_revision")}
    if evidence_id in {"rq2_structured_matrix", "rq2_v2_primary_matrix"}:
        return {"software_revision": _lookup(anchor, "provenance.software_revision")}
    if evidence_id == "rq2_v2_analysis":
        matrix = _read_json(repo_root / "backend/reports/benchmark_rq2_v2_google_gemini35flashlite_t01_20261121/execution_complete.json")
        return {
            "git_revision": _lookup(matrix, "provenance.git_revision"),
            "software_revision": _lookup(matrix, "provenance.software_revision"),
        }
    if evidence_id == "rq2_format_primary":
        protocol = _read_json(repo_root / "backend/reports/benchmark_format_equivalence_google_gemini35flashlite_20261120/protocol_manifest.json")
        return {"git_revision": protocol.get("git_revision"), "software_revision": protocol.get("software_revision")}
    if evidence_id == "rq2_format_post_recovery":
        recovery = _read_json(repo_root / "backend/reports/benchmark_format_equivalence_google_gemini35flashlite_selective_recovery_20261120/recovery_manifest.json")
        return {
            "primary_git_revision": recovery.get("primary_git_revision"),
            "recovery_git_revision": recovery.get("recovery_git_revision"),
            "software_revision": recovery.get("software_revision"),
        }
    return {}


def _counts(evidence_id: str, anchor: dict, repo_root: Path) -> dict:
    if evidence_id in {"rq1_student_panel", "rq1_expert_replication"}:
        return {key: anchor.get(key) for key in ("n_evaluators", "n_schemas", "n_ratings")}
    if evidence_id in {"rq2_structured_matrix", "rq2_v2_primary_matrix"}:
        return {key: anchor.get(key) for key in ("planned_runs", "ok", "error", "fallback")}
    if evidence_id == "rq2_gold_standard_consensus_v2":
        decisions = _read_json(repo_root / "backend/reports/gold_standard_consensus_20261121/consensus_decisions.json")
        return {
            "decision_count": decisions.get("decision_count"),
            "technical_consensus_status": decisions.get("technical_consensus_status"),
        }
    if evidence_id == "rq2_v2_analysis":
        result = _read_json(repo_root / "backend/reports/rq2_v2_analysis_20261121/rq2_v2_analysis.json")
        return {"run_count": result.get("run_count")}
    if evidence_id == "rq2_human_adjudication":
        summary = _read_json(repo_root / "backend/reports/rq2_adjudication_completed/final_adjudication_summary.json")
        return {key: summary.get(key) for key in ("item_count", "independent_agreement_count", "consensus_count")}
    if evidence_id == "rq2_format_primary":
        result = _read_json(repo_root / "backend/reports/rq2_format_analysis/rq2_format_analysis.json")
        return {key: result.get(key) for key in ("n_runs", "n_ok", "n_error")}
    if evidence_id == "rq2_format_post_recovery":
        result = _read_json(repo_root / "backend/reports/rq2_format_post_recovery_sensitivity/rq2_format_post_recovery_sensitivity.json")
        return {
            "primary_result_preserved": result.get("primary_result_preserved"),
            "recovery_overlays": result.get("recovery_overlays"),
            "post_recovery_result": result.get("post_recovery_result"),
        }
    return {}


def _verify_internal_outputs(repo_root: Path, checks: tuple[tuple[str, str], ...]) -> int:
    verified = 0
    for manifest_relative, field in checks:
        manifest_path = _safe_path(repo_root, manifest_relative)
        payload = _read_json(manifest_path)
        outputs = payload.get(field)
        if not isinstance(outputs, dict):
            raise ValueError(f"missing {field} hash map: {manifest_relative}")
        for name, expected in outputs.items():
            output = _safe_path(repo_root, (Path(manifest_relative).parent / name).as_posix())
            if sha256_file(output) != expected:
                raise ValueError(f"internal output hash mismatch: {output}")
            verified += 1
    return verified


def build_index(repo_root: Path, output_dir: Path, specs=EVIDENCE_SPECS) -> dict:
    repo_root = repo_root.resolve()
    components = []
    aggregate = hashlib.sha256()
    total_internal_hashes = 0
    for spec in specs:
        selected = []
        for relative in spec.files:
            path = _safe_path(repo_root, relative)
            _scan_for_secrets(path)
            digest = sha256_file(path)
            aggregate.update(relative.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\0")
            selected.append({"path": relative, "sha256": digest})
        anchor_path = _safe_path(repo_root, spec.anchor)
        anchor = _read_json(anchor_path)
        internal_count = _verify_internal_outputs(repo_root, spec.internal_outputs)
        total_internal_hashes += internal_count
        components.append({
            "evidence_id": spec.evidence_id,
            "rq": spec.rq,
            "classification": spec.classification,
            "anchor": spec.anchor,
            "revisions": {key: value for key, value in _revision_metadata(spec.evidence_id, anchor, repo_root).items() if value},
            "counts": {key: value for key, value in _counts(spec.evidence_id, anchor, repo_root).items() if value is not None},
            "selected_public_artifacts": selected,
            "internal_output_hashes_verified": internal_count,
        })
    script_path = Path(__file__).resolve()
    manifest = {
        "index_version": "rq1-rq2-evidence-index-v2",
        "status": "complete_automated_evidence_index",
        "scope": "RQ1 and RQ2 evidence, with consensus-amended RQ2 v2 current and v1 explicitly historical; RQ0 and RQ3 are reported in the separate available-record analysis",
        "components": components,
        "component_count": len(components),
        "selected_public_artifact_count": sum(len(item["selected_public_artifacts"]) for item in components),
        "internal_output_hashes_verified": total_internal_hashes,
        "aggregate_selected_artifacts_sha256": aggregate.hexdigest(),
        "index_script": {
            "path": script_path.relative_to(repo_root).as_posix(),
            "normalized_text_sha256": normalized_text_sha256(script_path),
        },
        "privacy": {
            "private_mapping_artifacts_indexed": False,
            "raw_participant_exports_indexed": False,
            "evaluation_timestamps_published": False,
        },
        "interpretation": "This index proves presence and integrity of selected public evidence; it does not convert exploratory or post-outcome analyses into confirmatory results.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Indice finale delle evidenze RQ1/RQ2",
        "",
        f"Stato: `{manifest['status']}`. Componenti: {manifest['component_count']}; artefatti pubblici selezionati: {manifest['selected_public_artifact_count']}.",
        "",
        "| Evidenza | RQ | Classificazione | Artefatti | Hash interni verificati |",
        "|---|---|---|---:|---:|",
    ]
    for item in components:
        lines.append(
            f"| `{item['evidence_id']}` | {item['rq']} | `{item['classification']}` | "
            f"{len(item['selected_public_artifacts'])} | {item['internal_output_hashes_verified']} |"
        )
    lines.extend([
        "",
        "L'indice non include mapping privati, export grezzi dei partecipanti o tempi di compilazione. "
        "La matrice RQ2 v2 post-consenso è l'evidenza corrente; le matrici v1 restano storiche. "
        "La matrice per formato resta primaria a 38/40; l'overlay 40/40 è una sensibilità secondaria post-outcome.",
        "",
        "RQ0 e RQ3 sono documentati separatamente nell'analisi dei registri disponibili.",
    ])
    (output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the final public RQ1/RQ2 evidence index.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "reports" / "research_evidence_index")
    args = parser.parse_args(argv)
    manifest = build_index(args.repo_root, args.output)
    print(json.dumps({
        "output": str(args.output),
        "components": manifest["component_count"],
        "artifacts": manifest["selected_public_artifact_count"],
        "internal_hashes_verified": manifest["internal_output_hashes_verified"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
