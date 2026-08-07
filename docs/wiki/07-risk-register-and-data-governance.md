# 07 - Risk Register & Data Governance Framework

> **Source Documents**: `docs/12-risk-register.md`, `docs/13-data-governance.md`

---

## 1. Risk Register & Mitigation Matrix

| Risk ID | Category | Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-01** | Security | Exposure of database credentials or LLM API keys | High | Low | Environment variable injection, zero hardcoded secrets in source code, strict `.gitignore` rules |
| **R-02** | Security | Keycloak token expiration during active user sessions | Medium | Medium | React `KeycloakContext` event listeners (`onTokenExpired`) calling `updateToken(30)` |
| **R-03** | Accuracy | LLM schema hallucinations (non-existent foreign key tables) | High | Medium | Pydantic structural validation + automatic relational reference check before execution |
| **R-04** | Performance| Long network latency or timeouts on remote LLM endpoints | Medium | High | Asynchronous `httpx.AsyncClient` calls with strict 5-second timeouts and fallback model resolution |
| **R-05** | Governance | Processing of PII (Personally Identifiable Information) in user documents | High | Medium | Full compliance with GDPR data minimization, document isolation per user ID, explicit data deletion API |

---

## 2. Data Governance & GDPR Compliance Framework

### 2.1 Data Classification & Multi-Tenancy Isolation
- **User Scoping**: Every `Project`, `Document`, and `InteractionLog` record is bound to the Keycloak Subject ID (`sub`).
- **Data Isolation**: Foreign keys ensure users can only access or modify records belonging to their authenticated identity.

### 2.2 Right to Erasure (GDPR Article 17)
- Executing `DELETE /api/projects/{id}` performs cascading deletion of:
  1. Project metadata from PostgreSQL
  2. Physical upload files from `/uploads`
  3. Provenance JSON manifests from `/projects/{id}/manifests/`
  4. Physical project databases

### 2.3 Data Retention Policy
- Benchmark logs and interaction metrics anonymize user IDs before aggregation.
- Raw document contents are retained solely for the duration of the active project session.
