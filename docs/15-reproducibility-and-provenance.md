# Reproducibility and Provenance Protocol

## Run Manifest

Every schema-generation and population execution must produce a stable `run_id` and a structured manifest containing:

- experiment condition and pseudonymous participant/session identifier when experiment mode is enabled;
- start/end timestamps in UTC;
- provider, exact model identifier returned by configuration, temperature and other exposed decoding parameters;
- prompt-template name and version;
- SHA-256 of the rendered prompt, source documents, input schema and output schema;
- software revision or release identifier;
- extraction path (`llm`, `deterministic`, or `hybrid`);
- counts of inserted, skipped and failed records;
- warnings, without raw credentials, bearer tokens, document text, SQL text or cell values.

The application configuration name is not proof of the provider's hidden serving revision. If a provider does not expose a dated immutable model version, record that limitation explicitly and archive raw outputs needed for replication in the restricted research-artifact directory.

## Provenance Record

For each automatically mapped value, retain the most precise available source coordinates:

- document ID and SHA-256;
- filename for participant-facing display, subject to filename-PII guidance;
- sheet name or PDF page when available;
- source row and column/header for tabular documents;
- target table, row key and column;
- mapping method;
- confidence in the closed interval `[0, 1]` and the rule used to derive it.

Confidence is evidence about the mapping method, not a calibrated probability of correctness unless calibration has been demonstrated on held-out gold data. Deterministic exact-header mapping may receive `1.0`; normalised/fuzzy rules and LLM mappings use lower, method-specific values and remain visibly labelled.

## Artifact Freeze

Before confirmatory data collection, freeze and identify:

1. application release;
2. environment and dependency lockfiles;
3. prompt templates;
4. three benchmark datasets and gold schemas;
5. task/tutorial version;
6. participant-facing forms and debrief wording; questionnaire wording and scoring only for a future protocol that actually enables them;
7. analysis scripts and preregistration.

Any material change after the first confirmatory participant creates a new protocol version. Runs from different protocol versions are never silently pooled.

## RQ1 Rating Analysis

The RQ1 ratings export is validated as a complete evaluator-by-schema matrix
before analysis. The analysis command records the source and mapping SHA-256,
software revision, deterministic bootstrap seed and resample count. Published
analysis artifacts use opaque evaluator identifiers and omit comments and the
identity-to-pseudonym correspondence. Authentic responses added to complete an
export are analysed as ordinary observations; the processing log records the
completion event without tagging individual participants or rows.

The planned protocol named three experts, whereas the observed export contains
45 evaluators. This is retained as a protocol deviation. Eligibility evidence
must be reviewed separately before the term “expert” is used confirmatorily.

## RQ0/RQ3/RQ4 Participant Analysis

The participant-study target is 34 completed cases in each of the Manual,
AI-Only, and AI + Interface arms. The application propagates only the random
participant ID and assigned arm across the study and app tabs. The backend
enforces arm restrictions for instrumented calls and records participant IDs in
run metadata without exporting account identifiers or withdrawal codes.

`backend/analyze_user_study.py` validates the three frozen exports, derives task
duration, applies the two preregistered contrasts, corrects the four primary
tests with Holm, and keeps RQ4 pattern, correlation, and clustering analyses
exploratory. Its manifest records input hashes, seed, bootstrap count, arm
counts, and the multiplicity family. Withdrawal also removes global interaction
events linked to the participant.

## Secret Handling

- Real `.env` files and generated logs/databases/uploads are excluded from version control.
- `.env.example` contains placeholders only.
- API keys are never included in manifests, exceptions, interaction payloads, exports or screenshots.
- A key found in a working tree or repository history is treated as compromised: rotate it at the provider, remove it from history where authorised, and document the incident without recording the key.

