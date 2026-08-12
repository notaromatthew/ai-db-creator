# AI-DB-Creator Scientific & Engineering Wiki Hub

> **Operational & Research Knowledge Base for AI Agents and Human Collaborators**  
> Navigation index for evolving draft specifications of **AI-DB-Creator**. Inclusion here does not imply implementation, validation, freeze or approval.

---

## 🗺️ Master Wiki Module Navigation

| Module | Title | Source Document Mapping | Primary Topics |
| :--- | :--- | :--- | :--- |
| 📖 **[01-project-overview-and-target-users.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/01-project-overview-and-target-users.md)** | Project Overview & User Profiles | `00-project-overview.md`, `03-user-manual.md` | Problem statement, target personas, core features, tech stack |
| 🤖 **[02-multi-agent-system-and-rfcs.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/02-multi-agent-system-and-rfcs.md)** | Multi-Agent Playbook & Agent RFC Log | `01-multi-agent-playbook.md`, `15-ai-agent-changelog.md`, `AGENTS.md` | Agent roles, operational constraints, structured RFC comment log |
| 🏛️ **[03-technical-architecture-and-cloud.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/03-technical-architecture-and-cloud.md)** | Architecture, Cloud & AGID | `02-technical-manual.md`, `05-cloud-maturity.md`, `06-agid-compliance.md` | Tech stack, PostgreSQL live schema, Keycloak OIDC, AGID, Cloud maturity |
| 🔌 **[04-api-dataflow-and-contracts.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/04-api-dataflow-and-contracts.md)** | API & Dataflow Handbook | `09-api-dataflow-map.md` | Exhaustive API endpoint reference, Pydantic schemas, flow diagrams |
| 🔬 **[05-research-methodology-and-provenance.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/05-research-methodology-and-provenance.md)** | Research Methodology & Provenance | `07-reverse-prompt.md`, `08-research-notes.md`, `15-reproducibility-and-provenance.md` | RQ0-RQ3, reverse prompt engineering, SHA-256 provenance manifests |
| 📊 **[06-benchmark-protocol-and-datasets.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/06-benchmark-protocol-and-datasets.md)** | Benchmark Protocol & Evaluation | `11-benchmark-protocol.md`, `16-manual-condition-protocol.md` | Datasets A/B/C, 3NF Formulas, Rel F1, Krippendorff's Alpha, Expert Rubric |
| 🛡️ **[07-risk-register-and-data-governance.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/07-risk-register-and-data-governance.md)** | Risk Register & Governance | `12-risk-register.md`, `13-data-governance.md` | Risk matrix, GDPR compliance, data retention, safety rules |
| 🚀 **[08-devops-coolify-and-sonarqube.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/08-devops-coolify-and-sonarqube.md)** | DevOps, Coolify & Quality | `04-deployment-guide.md`, `17-technical-review-dossier.md` | Coolify PaaS, Docker multi-stage, SonarQube quality gates, env vars |
| 📝 **[09-usability-pilot-and-results-draft.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/09-usability-pilot-and-results-draft.md)** | Usability Pilot & Results | `10-thesis-roadmap.md`, `14-usability-pilot-protocol.md`, `18-results-draft.md` | NASA-TLX, SUS, pilot user protocol, research results, thesis roadmap |

---

## 🤖 Instructions for AI Agents (AGENTS.md Directives)

- **Strict Strictness**: Never introduce fallback SQLite modes or bypass Keycloak JWT / PostgreSQL online database contracts.
- **Async Execution**: Ensure all HTTP calls to remote LLM services (Ollama, Gemini, Groq, OpenRouter) use `httpx.AsyncClient`.
- **RFC Logging**: Append code improvement proposals, architectural observations, and refactoring notes directly to [02-multi-agent-system-and-rfcs.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/02-multi-agent-system-and-rfcs.md).
- **Test Integrity**: Keep backend `pytest` (65/65 passed) and frontend `vitest` + `npm run build` clean at all times.
