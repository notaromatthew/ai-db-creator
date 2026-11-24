import csv
import json

from analyze_rq1_expert_replication import DIMENSIONS, main


def test_three_expert_panel_accepts_mixed_exports_is_pseudonymized_and_handles_constant_dimension(tmp_path):
    mapping_path = tmp_path / "mapping.csv"
    source_path = tmp_path / "experts_headerless.csv"
    third_source_path = tmp_path / "third_expert.csv"
    mapping = []
    for run in range(1, 16):
        mapping.extend([
            {"code": f"B{run:02d}", "dataset": "demo", "condition": "baseline", "run": f"run{run}"},
            {"code": f"F{run:02d}", "dataset": "demo", "condition": "full_llm", "run": f"run{run}"},
        ])
    with mapping_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mapping[0]))
        writer.writeheader()
        writer.writerows(mapping)

    with source_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        for evaluator in ("raw-one", "raw-two"):
            for index, meta in enumerate(mapping):
                value = 3 if meta["condition"] == "baseline" and index % 4 == 0 else 5
                writer.writerow([
                    evaluator, meta["code"], meta["dataset"], meta["condition"], meta["run"],
                    value, 5, value, value, value, "", "2026-11-11T10:00:00+00:00",
                ])

    with third_source_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "evaluator", "code", "dataset", "condition", "run",
            *DIMENSIONS, "comment", "updated_at",
        ])
        for index, meta in enumerate(mapping):
            value = 2 if meta["condition"] == "baseline" and index % 4 == 0 else 4
            writer.writerow([
                "raw-three", meta["code"], meta["dataset"], meta["condition"], meta["run"],
                value, 5, value, value, value, "", "2026-11-12T10:00:00+00:00",
            ])

    output = tmp_path / "analysis"
    assert main([
        "--input", str(source_path),
        "--input", str(third_source_path),
        "--mapping", str(mapping_path),
        "--output", str(output),
        "--bootstrap-resamples", "25",
    ]) == 0

    canonical = (output / "ratings_canonical_pseudonymized.csv").read_text(encoding="utf-8")
    assert "raw-one" not in canonical
    assert "raw-two" not in canonical
    assert "raw-three" not in canonical
    assert {row["evaluator_id"] for row in csv.DictReader(canonical.splitlines())} == {
        "X001", "X002", "X003"
    }
    assert "updated_at" not in next(csv.DictReader(canonical.splitlines()))

    agreement = {row["dimension"]: row for row in csv.DictReader(
        (output / "agreement.csv").read_text(encoding="utf-8").splitlines()
    )}
    assert agreement["d2_naming"]["alpha_ordinal"] == ""
    assert agreement["d2_naming"]["undefined_reason"] == "no_between_unit_variation"
    assert float(agreement["overall"]["exact_agreement_pct"]) < 100.0

    comparison = {row["dimension"]: row for row in csv.DictReader(
        (output / "condition_comparison.csv").read_text(encoding="utf-8").splitlines()
    )}
    assert comparison["d2_naming"]["welch_t_p"] == ""
    assert comparison["d2_naming"]["cohen_d"] == ""

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_evaluators"] == 3
    assert manifest["planned_evaluators"] == 3
    assert manifest["raw_evaluator_names_persisted"] is False
    assert manifest["evaluation_timestamps_published"] is False
    assert manifest["independence"] == "all_three_user_attested"
    assert manifest["condition_blinding"] == "all_three_user_attested"
    assert manifest["attestation_recorded_on"]["third_expert_independence"] == "2026-11-19"
    assert manifest["attestation_recorded_on"]["third_expert_condition_blinding"] == "2026-11-24"
    assert "completion_span_minutes_by_evaluator_id" not in manifest
    assert set(manifest["original_source_sha256"]) == {source_path.name, third_source_path.name}
    assert manifest["exact_score_cell_agreement"].endswith("/150")
