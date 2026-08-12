# RQ4 Interaction Event Taxonomy and Codebook — DRAFT / UNAPPROVED

> Proposed schema for data minimisation and reproducible analysis. It must be reconciled with actual logging, privacy review and pilot evidence before freeze.

## Event envelope

Every event has the fields defined in `docs/20-research-data-dictionary-draft.md`. `sequence_no` is monotonically increasing per session; `monotonic_ms` determines order when clocks drift. Events are append-only. Retries share `operation_id`; this prevents counting one user action multiple times.

## Controlled taxonomy

| Family | Event types | Count rule |
|---|---|---|
| navigation | `view_opened`, `tab_changed`, `help_opened` | state transition, suppress repeated render events |
| document | `document_upload_started/succeeded/failed`, `document_removed` | one terminal event per operation |
| generation | `schema_generation_started/succeeded/failed`, `regeneration_requested` | user request and terminal status separate |
| chat | `chat_prompt_submitted`, `suggestion_received`, `suggestion_accepted/rejected` | no raw prompt; length/category only if approved |
| schema edit | `table_added/removed/renamed`, `column_added/removed/renamed/type_changed`, `pk_changed`, `fk_changed`, `constraint_changed`, `relationship_changed` | one committed mutation; undo is separate |
| validation | `schema_review_started`, `schema_accepted`, `warning_viewed/overridden` | acceptance only after persisted artifact |
| population | `population_started/succeeded/failed`, `mapping_reviewed`, `cell_edited`, `row_added/removed` | never log raw values; target IDs hashed |
| query/export | `query_executed`, `export_started/succeeded/failed`, `submission_completed` | query category/hash, not SQL text |
| recovery | `undo`, `redo`, `backup_restored`, `retry`, `error_viewed` | link to operation/error code |
| study | `tutorial_started/completed`, `task_started/ended`, `questionnaire_started/completed`, `facilitator_intervention` | protocol events |

## Derived features

Predefine: total committed edits; edits by family; suggestion acceptance/rejection rate; warning override rate; chat count; regeneration count; time-to-first-review; review duration; edit-to-accept latency; undo/retry count; error recovery rate; distinct schema objects touched; sequence length; transition probabilities among `GENERATE`, `REVIEW`, `EDIT`, `POPULATE`, `QUERY`, `EXPORT`; and pre/post schema quality delta where a valid pre-edit artifact exists.

Denominators matter: acceptance rate uses received actionable suggestions; error recovery uses recoverable errors; edit rates use active task minutes. Do not infer “ignored suggestion” unless a suggestion was displayed and remained unresolved at task end.

## Sequence/session rules

Collapse technical duplicates with identical `operation_id`; retain failed attempts. Define inactivity gap `[freeze, proposed 5 minutes]` for active-time sensitivity only, never delete events. A session ends at submission, withdrawal or timeout. Concurrent tabs are ordered by server receipt plus client sequence and flagged as ambiguous when inconsistent.

## RQ4 analysis guardrails

Primary preregistered association candidates: committed constraint/FK edits, suggestion review rate and time spent reviewing versus final quality improvement. Adjust for baseline schema quality, dataset, experience and total active time. Clustering and Markov sequence discovery are exploratory; choose preprocessing and cluster-number rule before condition outcomes. Report stability under bootstrap and do not assign causal labels such as “effective behavior.”

## Privacy allow-list

Allowed payload: controlled event/category codes, booleans, counts, durations, hashed internal object IDs, error code, app/protocol version. Prohibited: names, emails, IP, filenames containing PII, raw document cells/text, chat text, SQL, credentials and free-form stack traces. Free-text feedback belongs in a separately governed dataset.
