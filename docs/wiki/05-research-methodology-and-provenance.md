# 05 - Research Methodology, Reverse Prompts & Provenance

> **Source Documents**: `docs/07-reverse-prompt.md`, `docs/08-research-notes.md`, `docs/15-reproducibility-and-provenance.md`

---

## 1. Core Research Questions (RQs)

AI-DB-Creator is designed to answer four foundational PhD research questions in AI-assisted software engineering:

- **RQ0 (End-to-End Efficacy)**: How does an LLM-powered visual schema design & population workflow compare with traditional manual relational database design for non-expert domain experts in terms of time, error rate, and cognitive load?
- **RQ1 (Schema Generation Quality)**: To what extent do LLMs generate 3NF-compliant relational schemas from natural language domain descriptions and multi-document inputs across varying complexity tiers?
- **RQ2 (Population Ingestion & Provenance)**: How accurately do LLMs map heterogeneous tabular/unstructured documents into relational tables compared to deterministic header matching, and how can cell provenance be tracked reliably?
- **RQ3 (Human-in-the-Loop Interventions)**: What impact do interactive user refinements (chat corrections, schema edits, Likert expert ratings) have on overall schema quality and usability?

---

## 2. Reverse Prompt Engineering Strategy (`docs/07-reverse-prompt.md`)

To force LLMs to output 3NF-compliant relational schemas without hallucinations or syntax errors, system prompts enforce a strict 4-step chain-of-thought:

1. **Entity Identification**: Extract domain entities and assign normalized table names in `snake_case`.
2. **Attribute Decomposition & Data Typing**: Map properties to standard SQL data types (`INTEGER`, `VARCHAR`, `TEXT`, `FLOAT`, `BOOLEAN`, `DATETIME`).
3. **Primary Key & Foreign Key Enforcement**: Enforce single-column or composite primary keys and map foreign keys exclusively to valid target primary keys.
4. **JSON Output Strictness**: Format the output as a valid `NormalizedSchema` JSON matching the Pydantic schema without markdown commentary outside the JSON block.

---

## 3. Experimental Provenance & Reproducibility System

Every execution within the platform generates an immutable provenance record:

- **`run_id`**: Deterministic UUID generated from `sha256_text(prompt + provider + model + timestamp)`.
- **Manifest Logging** (`app/utils/research.py`):
  - Saves full JSON manifests in `backend/projects/{project_id}/manifests/{run_id}.json`.
  - Records input document SHA-256 hashes (`sha256_file`).
  - Logs exact hyperparameter states (`temperature`, `top_p`, `max_tokens`, `llm_provider`).
- **Reproducibility Guarantee**: Allows researchers to re-execute any benchmark scenario under identical prompt, seed, and temperature conditions to verify statistical comparability.
