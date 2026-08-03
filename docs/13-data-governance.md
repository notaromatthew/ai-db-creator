# Data Governance Document

## 1. Purpose and Scope

This document describes the data governance framework for AI-DB-Creator, a PhD research platform. It specifies what data is collected, how it is stored, processed, and retained, and what protections are in place for research participants. This framework is designed to comply with:

- **GDPR** (General Data Protection Regulation, EU) — for studies involving EU-based participants
- **UK Data Protection Act 2018** — for studies based at UK universities
- **University ethics committee guidelines** — as applicable to the host institution
- **Google Gemini API Privacy Policy** — for data processed via Google's LLM API

---

## 2. Data Collected

### 2.1 Interaction Logs

Every user action within the AI-DB-Creator interface is logged with the following fields:

| Field | Type | Example | Notes |
|---|---|---|---|
| `timestamp` | ISO 8601 datetime | `2026-07-31T14:30:00.000Z` | UTC |
| `event_type` | String | `schema_saved` | Controlled vocabulary (see API Dataflow Map) |
| `project_id` | UUID v4 | `a1b2c3d4-...` | Referenced to project, not to participant |
| `data` | JSON object | `{"tables": 3, "columns": 10}` | Event-specific; contains no personal data |
| `run_id` | UUID v4 | `95f6...` | Links events from one generation/population run |
| `condition` | Enum | `ai_ui` | `manual`, `ai_only`, or `ai_ui` |
| `model_config` | JSON object | `{"provider":"openai","model":"...","temperature":0}` | Contains no API key or credentials |
| `input_hashes` | JSON object | `{"prompt_sha256":"...","documents_sha256":["..."]}` | Reproducibility without duplicating raw content |
| `state_hashes` | JSON object | `{"before":"...","after":"..."}` | Detects state transitions without storing cell values |

Event types include:
- `document_upload` — filename (original filename is stored; user should avoid PII in filenames)
- `document_delete` — document ID only
- `schema_generated`, `schema_accepted`, `schema_saved` — table/column counts, schema hash, prompt-template version, model configuration, and before/after hashes; full schema snapshots are stored only in the project research artifact directory
- `populate` — per-table insertion counts, extraction method (`deterministic`, `hybrid`, or `llm`), source coordinates, run metadata, and confidence only when defined; uncalibrated method scores are never presented as probabilities of correctness
- `data_row_update`, `data_row_insert`, `data_row_delete` — table name and column count, not cell values
- `execute_query` — query type (SELECT vs. write), row/column counts, **not the SQL text**
- `backup`, `restore` — backup filename (timestamp-based, no user-identifiable information)
- `import_sql` — dialect and table count

### 2.2 Survey Responses

Two validated instruments are collected:

**Raw NASA-TLX (6 items):** Mental demand, physical demand, temporal demand, performance, effort, frustration — each rated 0–100. The aggregate score is the arithmetic mean of the six ratings. No free-text fields.

**SUS (10 items):** Standard System Usability Scale questions — each rated 1–5. No free-text fields.

Survey responses include a `project_id` reference but **no participant name, email, or identifier**.

### 2.3 Usage Metrics (Implicit)

- Request timestamps and endpoint paths (from Uvicorn access logs)
- Task completion times (from Celery task metadata)
- Error rates and types (from Loguru logs)

---

## 3. Data NOT Collected

The following are **explicitly not collected** by the AI-DB-Creator system:

| Category | Examples | Reason |
|---|---|---|
| **Personal identifiers** | Name, email, phone number, address, IP address | Not required for research; IP is not logged by default |
| **Document content in interaction logs** | Extracted PDF text, CSV/Excel cell values | Original files and a bounded extraction summary are stored in the project workspace; interaction events contain only hashes, counts, source coordinates, and method/confidence metadata. Extracted content may be transmitted to the configured external LLM provider as described in Section 7. |
| **Chat message text (persistent)** | Free-text messages sent to the schema chat | Chat history is maintained per session for context but is not stored in interaction logs; only the schema output is saved |
| **SQL query text** | The actual SQL generated or executed | Only metadata (SELECT vs. write, row/column counts) is logged |
| **Biometric data** | Keystroke dynamics, mouse tracking, eye gaze | Not instrumented |
| **Browser fingerprint** | User agent, screen resolution, installed fonts | Not collected |
| **Credentials** | API keys, bearer tokens, `.env` values | Redacted at the logging boundary and excluded from exports |

---

## 4. Data Storage

### 4.1 Storage Locations

| Data Type | Location | Format | Access |
|---|---|---|---|
| Interaction logs | `backend/projects/interactions_store.json` | JSON array | Backend service account (file system) |
| Per-project interaction export | `backend/projects/{project_id}/interactions.json` | JSON file | On-demand export via API |
| Survey responses | `backend/projects/surveys/` | Individual JSON files | Backend service account |
| Uploaded documents | `backend/uploads/` | Original file formats | Backend service account |
| Generated databases | `backend/projects/{project_id}/database.sqlite` | SQLite | Backend service account |
| Application state | `backend/app.db` | SQLite | Backend service account |

### 4.2 Encryption

- Data at rest: stored on the university's encrypted file system (requires institutional setup).
- Data in transit: HTTPS should be configured for production deployments. The development server (Uvicorn) uses HTTP.
- API keys: stored in `.env` file, which is excluded from version control via `.gitignore`.

### 4.3 Access Control

- The backend service account has file system access to all data.
- No other users or services can access the storage directories.
- No data is transmitted to third parties except as described in Section 7 (LLM API calls).

---

## 5. Anonymization Procedures

### 5.1 During Collection

- Participant IDs are assigned and used in place of names. No mapping of participant ID to real identity is stored in the system.
- Project names are user-provided. Participants are instructed to use descriptive (not personally identifying) project names.
- Document filenames may contain personal data (e.g., "John_Smith_data.csv"). Participants are instructed to rename files before uploading. The system does not automatically scrub filenames.

### 5.2 For Publication

Before publishing any experimental data:

1. All interaction logs are reviewed for accidental personal data (e.g., a document filename that includes a name).
2. Project IDs (UUIDs) are replaced with sequential numeric IDs (`P001`, `P002`, ...).
3. Survey responses are aggregated; individual responses are only reported anonymously.
4. Any generated database containing synthetic data based on real documents is reviewed before sharing as supplementary material.
5. The mapping from original project IDs to anonymised IDs is stored separately from the research data.

---

## 6. Data Retention Policy

| Data Type | Retention Period | Rationale |
|---|---|---|
| Interaction logs | Until 5 years after PhD award | Standard academic research retention; allows verification of results |
| Survey responses | Until 5 years after PhD award | Same as above |
| Uploaded documents | Deleted after 1 year or on participant request | Original files are not needed for verification; processed data (text extraction) is sufficient |
| Generated databases | Until 5 years after PhD award | Needed for RQ2 replication |
| Backups | Retained for duration of the project | System recovery purposes |

### 6.1 Deletion Procedure

Upon request or at the end of the retention period:
1. Delete all files in `backend/projects/{project_id}/`.
2. Delete the `project` and `document` records from `app.db`.
3. Delete all interaction log entries referencing the project ID.
4. Delete all survey response files referencing the project ID.

---

## 7. LLM Provider Data Handling

### 7.1 What Is Sent to LLM Providers

When generating a schema or populating data, the backend sends:

1. **Prompt text** — the system prompt (fixed, no user data) + user prompt (user-typed description)
2. **Document text** — bounded `content_summary` values from uploaded documents (up to 5,000 characters per document; combined prompts have an additional provider-call limit)
3. **Generated schema** — the current `NormalizedSchema` JSON (for incremental chat refinement)

### 7.2 Google Gemini API Privacy Policy

When using Google Gemini as the LLM provider (`LLM_PROVIDER=google`):

- Check the current [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms) immediately before the pilot and freeze the reviewed terms/date in the protocol manifest.
- Under the terms effective 23 March 2026, API clients made available to users in the EEA, Switzerland, or the UK may use only Paid Services. The account/service classification must therefore be verified before participant access; a free testing key is not assumed suitable for the experiment.
- Paid Services state that prompts/responses are not used to improve Google products, subject to the applicable data-processing terms and limited safety/abuse processing. Do not enable voluntary log sharing for research documents.
- **Mitigation:** Do not send personal, sensitive, or confidential documents through an unverified service tier. Prefer an institution-approved paid project with the required agreement, or local Ollama for sensitive material.

### 7.3 OpenAI API Privacy Policy

When using OpenAI (`LLM_PROVIDER=openai`):

- Check the current [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint) immediately before the pilot and record the reviewed terms/date.
- API inputs/outputs are not used for model training by default unless the organisation opts in.
- Default abuse-monitoring logs may retain customer content for up to 30 days, subject to endpoint-specific application-state retention and legal exceptions. Zero Data Retention or Modified Abuse Monitoring requires eligibility and explicit organisation/project configuration; it must not be assumed from the API key alone.
- The ethics/consent materials must identify the exact endpoint, storage setting and region used during data collection.

### 7.4 Local Processing (Ollama)

When using Ollama (`USE_OLLAMA=true`):
- No data leaves the local machine.
- All processing is done on-premises.
- This is the recommended configuration for processing sensitive or personal data.

---

## 8. GDPR Considerations

### 8.1 Lawful Basis

The lawful basis for processing personal data in this research is **Article 6(1)(e) — public task** (scientific research) and **Article 9(2)(j) — archiving / scientific research** for special category data, subject to suitable safeguards (Data Protection Act 2018, Schedule 1).

### 8.2 Data Subject Rights

Participants have the right to:

| Right | Implementation |
|---|---|
| **Right to be informed** | Provided via informed consent form and this governance document |
| **Right of access** | Participants can request a copy of their data (logs, surveys) |
| **Right to rectification** | Participants can ask to correct inaccurate data |
| **Right to erasure** | Participants can withdraw consent and have their data deleted |
| **Right to restrict processing** | Available on request |
| **Right to data portability** | Logs and surveys can be exported as JSON |
| **Right to object** | Available for scientific research processing |

### 8.3 Data Controller

The university / research institution hosting the study is the data controller. The PhD student (researcher) is the data processor. Contact details are provided in the informed consent form.

---

## 9. Informed Consent Requirements

### 9.1 Consent Form Content

Participants in the user experiment (Phase 5) must read and sign a consent form covering:

1. **Purpose of the study** — to evaluate an AI-powered database creation tool
2. **Task description** — what they will do during the session
3. **Data collected** — interaction logs, survey responses (no personal data)
4. **Data handling** — storage, retention, anonymisation
5. **LLM API data use** — that their document text and prompts will be sent to an external LLM API
6. **Risks** — minimal (standard computer use)
7. **Voluntary participation** — can withdraw at any time without penalty
8. **Contact information** — researcher and ethics committee contact details

### 9.2 Withdrawal Procedure

If a participant withdraws:
1. Their session is terminated immediately.
2. All data associated with their project ID is deleted within 48 hours.
3. They receive confirmation of deletion via email (if contact was provided for this purpose).
4. After PhD award, withdrawal is not possible (data fully anonymised).

---

## 10. Compliance Checklist

| Requirement | Status | Notes |
|---|---|---|
| Ethics approval obtained | Pending | To be submitted in Phase 2 |
| Data Protection Impact Assessment (DPIA) | Pending | Required if processing personal data |
| GDPR-compliant consent form | Drafted (this document) | Needs institutional template integration |
| Data retention schedule documented | Yes | Section 6 |
| Anonymization procedure documented | Yes | Section 5 |
| LLM provider data handling documented | Yes | Section 7 |
| Participant right to erasure implemented | Partial | Procedure documented in Sections 6.1 and 9.2; automated cross-store deletion must pass the release QA checklist before recruitment |
| Data breach notification procedure | Not documented | To be added; notify ethics committee within 72 hours |
| Secure data storage implemented | Partial | Needs institutional encrypted storage |
