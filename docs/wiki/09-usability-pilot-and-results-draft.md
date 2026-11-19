# 09 - Usability Pilot Protocol & Experimental Results

> **Source Documents**: `docs/10-thesis-roadmap.md`, `docs/14-usability-pilot-protocol.md`, `docs/18-results-draft.md`

---

## 1. Usability Pilot Study Protocol

The current RQ0/RQ3 pilot evaluates objective task outcomes and workflow failures with participants from non-technical disciplines. It does not collect perceived cognitive-load or usability questionnaires.

### Current evaluation instruments

- schema quality and residual error rate;
- task success and completion time;
- pseudonymous interaction events;
- optional privacy-filtered debrief.

NASA-TLX and SUS are reserved for a possible future revision and must not be mixed with the current study.

---

## 2. Preliminary Benchmark Results Draft (`docs/18-results-draft.md`)

Evaluation results across models and complexity tiers demonstrate clear performance trade-offs:

| Model / Provider | Dataset A (Simple) 3NF % | Dataset B (Medium) 3NF % | Dataset C (Complex) 3NF % | Avg Rel F1 | Latency (s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ollama Remote (`gemma2:9b`)** | 98.2% | 94.5% | 89.1% | 0.92 | 1.84s |
| **Ollama Remote (`llama3.2:1b`)** | 92.0% | 85.1% | 76.4% | 0.81 | 0.65s |
| **Google Gemini (`gemini-2.0-flash`)**| 99.1% | 96.2% | 92.8% | 0.95 | 1.21s |
| **OpenAI (`gpt-4o-mini`)** | 99.5% | 97.0% | 94.2% | 0.96 | 1.45s |

---

## 3. PhD Thesis Roadmap & Milestones

1. **Phase 1: Architecture & Auth Hardening** (Completed): PostgreSQL live database integration, Keycloak OIDC authentication, Remote Ollama model selection.
2. **Phase 2: Full-LLM Ingestion & Data Provenance** (Completed): Ingestion of CSV/PDF files, SHA-256 manifest generation.
3. **Phase 3: Controlled Pilot & Expert Panel** (Current): expert evaluation and objective participant outcomes without NASA-TLX or SUS.
4. **Phase 4: Thesis Writing & LaTeX Publication** (Next): Automated LaTeX export (`GET /api/benchmark/export-latex`), paper submission.
