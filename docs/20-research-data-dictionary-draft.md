# Research Data Dictionary — DRAFT / UNAPPROVED

> Proposed minimum analytic contract. It contains no participant data and must be reviewed against the final ethics/privacy decision before collection.

## Conventions

- One pseudonymous `participant_id`; the re-identification key, if any, is stored separately by an authorised custodian.
- UTC ISO-8601 timestamps; durations in integer milliseconds.
- Missing values use blank/NA plus a `missing_reason`, never invented sentinel scores.
- Arms: `manual`, `ai_only`, `ai_interface`. Datasets: frozen identifiers, not filenames.
- Direct identifiers, document text, SQL/cell values, tokens and credentials are prohibited in research logs.

## Participant/session table

| Variable | Type / values | Role | Sensitivity |
|---|---|---|---|
| participant_id | random string | join key | pseudonymous |
| session_id | random string | session key | pseudonymous |
| protocol_version | string | freeze/audit | public metadata |
| assigned_arm | enum | exposure | research |
| dataset_id | enum | block/covariate | research |
| allocation_stratum | enum | stratification | research |
| db_experience | ordinal, frozen categories | covariate | personal |
| computer_literacy | validated/frozen scale | covariate | personal |
| consent_version | string | governance | sensitive metadata |
| consent_timestamp | datetime | governance; separate table preferred | sensitive metadata |
| task_started_at / ended_at | datetime | timing | behavioural |
| completion_status | completed, partial, abandoned, technical_failure | outcome | research |
| exclusion_status / reason | boolean / controlled code | flow | research |
| withdrawal_deletion_at | datetime/NA | governance | sensitive metadata |

Do not collect age, gender, disability, institution or IP address unless justified in the approved protocol. If collected, define bins/minimisation and access restrictions before deployment.

## Artifact/outcome table

| Variable | Type | Definition |
|---|---|---|
| artifact_id | string | blinded artifact identifier |
| artifact_sha256 | hex string | integrity reference |
| schema_composite | 1–5 float | mean D1–D5 when ≥4 dimensions rated |
| d1_3nf … d5_domain | 1–5 ordinal | expert ratings retained per rater in long form |
| residual_error_count | non-negative integer | frozen rubric count |
| relationship_tp/fp/fn | integer | deterministic relation comparison |
| canonical_gold_facts | integer | `|G|`, primary RQ2 denominator |
| canonical_predicted_facts | integer | `|P|`, precision denominator |
| canonical_tp/fp/fn | integer | multiset fact comparison |
| canonical_fact_precision/recall/f1 | 0–1 | primary RQ2 metrics |
| strict_cell_* | numeric | supplementary physical representation metric |
| workload_query_success_rate | 0–1 | successful query execution / frozen queries |
| workload_answer_fact_f1 | 0–1 | canonical answer facts |
| workload_integrity_pass_rate | 0–1 | passed / eligible checks |
| sus_score | 0–100 | standard SUS scoring only |
| raw_nasa_tlx | 0–100 | arithmetic mean of six raw dimensions |
| completion_time_ms | integer | task start through valid export/submission |

## Event table

Required fields: `event_id`, `session_id`, `sequence_no`, `event_time_utc`, `monotonic_ms`, `event_type`, `object_type`, `object_id_hash`, `source_surface`, `success`, `error_code`, `duration_ms`, `protocol_version`, `app_revision`, `payload_schema_version`. Optional payload fields must be allow-listed in `docs/26-rq4-event-taxonomy-draft.md`.

## Expert ratings and adjudication

Long-form fields: `artifact_id`, `rater_id`, `presentation_order`, `rubric_version`, `dimension`, `score`, `reason_code`, `comment_redacted`, `rated_at`, `missing_reason`. Alignment decisions: `dataset_id`, `gold_concept`, `generated_concept`, `reviewer_a`, `reviewer_b`, `agreement`, `adjudicated_mapping`, `reason_code`, `decision_version`; reviewers never receive arm or outcome values.

## Benchmark run manifest

Include `run_id`, attempted/success status, condition, dataset, provider/model and exposed revision, decoding parameters, seed support, prompt/version/hash, document hashes, schema/database hashes, application/dependency revision, evaluator version/hash, alignment hash, canonicalisation hash, workload hash, start/end, warnings and failure code. Raw content is referenced only through restricted artifact IDs and hashes.

## Retention and access placeholders

Controller, lawful basis, processor/subprocessor list, storage region, retention interval, deletion SLA, access roles and incident contact are `[UNAPPROVED — complete with DPO/ethics review]`. Aggregate public releases must pass disclosure review; pseudonymous event-level data are not automatically anonymous.
