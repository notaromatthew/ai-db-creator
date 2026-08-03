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
6. questionnaire wording and scoring;
7. analysis scripts and preregistration.

Any material change after the first confirmatory participant creates a new protocol version. Runs from different protocol versions are never silently pooled.

## Secret Handling

- Real `.env` files and generated logs/databases/uploads are excluded from version control.
- `.env.example` contains placeholders only.
- API keys are never included in manifests, exceptions, interaction payloads, exports or screenshots.
- A key found in a working tree or repository history is treated as compromised: rotate it at the provider, remove it from history where authorised, and document the incident without recording the key.

