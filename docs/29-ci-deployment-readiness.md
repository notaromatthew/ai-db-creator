# CI and deployment readiness

The CI reports two independent outcomes. `software_checks=pass` means tests,
offline simulation, package verification and the versioned expectation check
passed. It does not mean the research materials are frozen. At present
`pilot_readiness=blocked` and `confirmatory_eligibility=blocked`: the hospital
dataset contains declared natural keys that are not unique and all functional
workloads remain draft. `check_research_gate.py` exits zero only while this
known state matches `data/datasets/research-gate-expectations.json`; any new or
missing blocker fails CI.

Run the same offline gate on Windows, macOS or Linux from `backend`:

```text
python -m pytest -q
python participant_simulator.py --output reports/participant-simulation
python check_research_gate.py
python research_readiness.py --root .. --gate software
```

The reproducibility ZIP is a public, de-identified report package. Full run
artifacts, databases, uploads and participant/session stores are restricted
research data and must never be placed in that ZIP or uploaded as CI artifacts.
The exporter and verifier enforce this boundary and hashes provide integrity,
not a cryptographic signature.

## Deployment safety

Copy environment values from `backend/.env.example` into a deployment secret
store. Never commit `.env`. Settings endpoints are administrator-only, never
return secret values, and do not persist runtime changes to `.env`. Provider
secrets and `OLLAMA_BASE_URL` are deployment-managed. The Ollama discovery and
test endpoints use only that configured URL, send keys in an Authorization
header and verify TLS.

When `EXPERIMENT_MODE=true`, unique non-placeholder values are mandatory for
`EXPERIMENT_ASSIGNMENT_SEED`, `EXPERIMENT_PSEUDONYM_SECRET` and
`RQ4_HASH_SALT`; startup fails otherwise. Keycloak realm bootstrap is disabled
by default (`BOOTSTRAP_KEYCLOAK=false`) and should be a separately authorized
administrative action.

`docker compose` keeps PostgreSQL and Redis off public host ports, waits for
dependency health and persists application state in named volumes. Compose
requires `REDIS_PASSWORD` and uses it for the Redis server, health check,
backend and worker URL. Use a long URL-safe value from the deployment secret
store; never commit it. Application defaults target localhost-only development
services and SQLite, so remote endpoints must be supplied explicitly through
the deployment configuration. The global LLM throttle defaults to 8 requests
per minute. Back up the
PostgreSQL and project/upload volumes according to the approved retention
policy; CI reports expire after 14 days.

Alembic is executed before the backend starts. The versioned migration chain is
tested on an empty database, the historical initial revision, and a current
pre-Alembic database. Current pre-Alembic schemas are verified column by column
before being stamped. Unknown or partial legacy layouts fail closed and require
a reviewed, backup-first migration; they are never guessed or silently changed.

CI also runs dependency audits, emits CycloneDX SBOM artifacts, scans the
repository with Trivy, starts all six Compose services, checks their health and
exercises a real Keycloak-issued bearer token with an ephemeral test user.
