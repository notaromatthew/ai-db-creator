# Functional Equivalence Workload — DRAFT / UNAPPROVED

> Secondary RQ2 protocol. Workloads and expected outputs remain exploratory until domain review and freeze. Functional equivalence is task-relative and does not replace canonical fact fidelity.

Implementation contract: the dataset file is `functional_workload.json`, the
configuration protocol is `functional_workload_v1`, and evaluator reports use
version string `functional-workload-v1`. Results have status
`exploratory_only` unless `approval_status` is exactly `frozen`; only then can
the evaluator label them `confirmatory_eligible`. Eligibility is necessary but
does not itself constitute protocol or ethics approval.

## Purpose and unit

A database can use different normalized decompositions or synthetic keys while answering the same domain questions. For each dataset, freeze a workload manifest with `approval_status`, version/hash, query ID, requirement, parameters, expected canonical answer facts, cardinality/ordering semantics, eligible conditions and integrity checks.

The evaluator may adapt SQL to a generated schema only through a mapping frozen before score inspection. A query that cannot be expressed because required information is absent is a failed query, not excluded.

## Workload design

Include at least: entity lookup, filtered list, join across a relationship, aggregation, missing/optional value, many-to-many traversal where applicable, temporal condition where applicable, and one negative/integrity case. Requirements must be derivable from source documents; do not reward invented features. Avoid redundant queries whose answers are the same facts unless explicitly weighted.

Two domain/database reviewers independently verify coverage and expected results, blind to generated outcomes; disagreements are adjudicated and logged. Pilot queries are separated from confirmatory queries where feasible.

## Deterministic scoring

- Query success rate = executed eligible queries / all frozen queries.
- Answer fact precision/recall/F1: compare canonical multisets; wrong answer values produce FP and FN.
- Exact answer-set match rate: equality after frozen canonicalisation; ordering ignored unless required.
- Integrity pass rate = passed checks / all frozen eligible checks.
- Overall functional score is not created unless weights and formula are preregistered.

The current machine-readable output contains `query_success_rate`,
`answer_fact_metrics` and `answer_cell_metrics` (each with TP, FP, FN,
precision, recall and F1), `integrity` (`sqlite_integrity` and
`foreign_key_violations`), per-query records and `config_hash`. Reports must
retain the evaluator version and eligibility status.

Report every denominator and error code: `SCHEMA_UNMAPPABLE`, `QUERY_BUILD_FAILED`, `EXECUTION_ERROR`, `TIMEOUT`, `WRONG_CARDINALITY`, `WRONG_VALUE`, `MISSING_VALUE`, `EXTRA_VALUE`, `INTEGRITY_FAIL`. Timeouts and unexpressible requirements count as failures. Query adaptation failures are not silently removed.

## Bias controls

No LLM judges answers or writes expected results for confirmatory scoring. If an LLM proposes candidate workloads, reviewers validate them before freeze and provenance is recorded. Workload authors cannot revise tests after seeing which arm fails. Report per-query results to expose workload dependence.

## Proposed manifest contract

```json
{
  "protocol": "functional_workload_v1",
  "approval_status": "draft",
  "dataset": "example",
  "canonicalisation_version": "[hash]",
  "queries": [{"id":"Q01","requirement":"[text]","parameters":{},"order_matters":false,"expected_result":"[restricted artifact]"}],
  "integrity_checks": [{"id":"I01","requirement":"[text]","expected":true}]
}
```

## Pre-freeze validation blocker

At the current draft checkpoint, validation identifies non-unique declared
entity keys in the hospital dataset for `treatments` and `prescriptions`.
Hospital workload/fact results are invalid until the gold data or entity-key
manifest is corrected, independently reviewed and rehashed. Do not weaken the
uniqueness check or omit these entities to make the manifest pass.
