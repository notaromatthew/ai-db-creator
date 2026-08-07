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
