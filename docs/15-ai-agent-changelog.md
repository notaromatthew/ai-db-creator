# AI Agent Changelog: Differences Introduced in Branch `Davide`

This document provides a machine-readable summary of architectural, model, API, and environmental changes introduced in branch `Davide` relative to `main`.

---

## 1. Summary of Major Additions

- **PostgreSQL Online Database Integration**: Primary application database target migrated to online PostgreSQL (`89.168.29.98:12000`). SQLite local fallback remains active if PostgreSQL connection fails.
- **Keycloak OIDC Authentication & Realm Setup**: Multi-tenant project isolation by `user_id` (JWT Bearer token verification). Automatic Realm (`aidbcreator`) and Client (`aidbcreator-app`) provisioning on startup.
- **SonarQube Integration**: Static code analysis setup configured for `http://o4sn9bs961jvxn32hs18a81p.89.168.29.98.sslip.io:9000`.
- **Project Wizard & Help System**: Modal for choosing between Quick Mode and Guided Step-by-Step Wizard; interactive `/help` documentation page.
- **Dynamic AI Hyperparameter Configuration**: `/settings` API and UI to tune LLM Provider, Temperature, Top-P, Max Tokens, and Rate Limits.
- **Scientific Benchmark & Expert Voting Module**: `/benchmark` page evaluating 3NF %, Relationship F1, Cell Precision, Latency, Token Cost, Likert 1-5 Human Expert voting, and LaTeX table export.
- **Coolify PaaS Deployment Ready**: Multi-stage `Dockerfile` and `docker-compose.coolify.yml`.

---

## 2. Model & Database Schema Modifications

### Table: `projects`
- Added column: `user_id` (`String(255)`, indexed, nullable). Filters projects by authenticated Keycloak user.

### Table: `benchmark_results` (NEW)
- Columns: `id`, `scenario_name`, `provider`, `model_name`, `norm3_score`, `relationship_f1`, `cell_precision`, `latency_seconds`, `token_cost_estimate`, `details_json`, `created_at`.

### Table: `user_votes` (NEW)
- Columns: `id`, `project_id`, `benchmark_id`, `user_id`, `schema_rating`, `data_rating`, `comment`, `created_at`.

---

## 3. New API Endpoints

- `GET /api/settings` - Retrieve current AI provider and hyperparameter settings.
- `PUT /api/settings` - Update AI provider, model names, temperature, top_p, max_tokens, rate limit.
- `GET /api/benchmark/scenarios` - List available Gold Standard benchmark scenarios.
- `POST /api/benchmark/run` - Execute automated benchmark test run.
- `GET /api/benchmark/results` - Fetch historic benchmark runs and human expert votes.
- `POST /api/surveys/vote` - Record human expert subjective evaluation (Likert 1-5 & comments).

---

## 4. Impact on Experimental Comparability (per AGENTS.md)

- **Deterministic Fallbacks & LLM Prompts**: Intact. Benchmark evaluations run on isolated test scenarios without altering project schemas.
- **Environmental Contracts**: Backend functions gracefully fallback to SQLite if PostgreSQL is offline, and authentication defaults to `default-user` if `ENABLE_AUTH=False`.


---

## Branch `redesign/tecnia-research`: ridisegno, ACL e modalità ricerca

- **ACL**: tabelle `users`, `project_members`, `project_invites`, `project_links`; `projects.owner_id` sostituisce `user_id`. Ruoli owner/editor/viewer, 404 sui progetti inaccessibili, link pubblico di sola lettura, admin tramite ruolo Keycloak `aidb-admin` (metadati e consumi, mai contenuti altrui). Controllo unico in `app/core/acl.py`.
- **RESEARCH_MODE**: variabile d'ambiente (default spento). Spenta, benchmark, questionari, log delle interazioni ed esperimenti rispondono 404 e resta solo il prodotto. `GET /api/config` espone la modalità al frontend.
- **Admin e quote**: `app_settings`, `admin_audit_log`, `usage_events`; quote giornaliere basse per utente e tetto globale; `/api/admin/*`.
- **Sicurezza** (revisione indipendente): `execute-query` con autorizzatore SQLite (niente ATTACH/PRAGMA, lettori in sola lettura), path traversal in `restore` chiuso, `/progress` protetto, questionari ed esperimenti vincolati al progetto, inviti accettati solo con email verificata (impostazione `invites_require_verified_email`), verifica dell'issuer del token e ricarica del JWKS, impostazioni e chiavi API solo admin e mascherate, nessuna credenziale di default per il database.
- **Migrazioni**: `run_migrations` all'avvio (database nuovo: stamp; database precedente: migrazione con proprietario `legacy` ai progetti orfani). Migrazioni `d1a0acl00001`, `d2adm00002`, `d3chat00003`.
- **Chat**: cronologia salvata su database (`chat_messages`).
- **Frontend**: tema TecnIA, landing `/` e `/en/`, app su `/app`, registrazione Keycloak, flusso a 4 passi con barra azioni fissa, diagramma ER con chat laterale fino a "Rendi definitivo", scelta del dialetto, condivisione, pagina admin, vista pubblica.
- **Infra**: `infra/gcp` (Terraform per Vertex AI, validato, non applicato).
