# Staging

`docker-compose.staging.yml`: stessi servizi della produzione (`app-staging`, `worker-staging`, `redis-staging`), stessa immagine (stesso `Dockerfile`), nomi e volume distinti (`redis_staging_data`), tutte le variabili con prefisso `STAGING_*`. Nessun segreto nel file.

## Variabili da creare in Coolify (ambiente staging)
`STAGING_DATABASE_URL` (database separato, mai quello di produzione), `STAGING_REDIS_PASSWORD`, `STAGING_KEYCLOAK_URL`, `STAGING_KEYCLOAK_REALM` (default `aidbcreator-staging`), `STAGING_KEYCLOAK_CLIENT_ID`, `STAGING_KEYCLOAK_ADMIN_USER/PASSWORD`, `STAGING_APP_PUBLIC_URL`, `STAGING_LLM_GATEWAY_URL`, `STAGING_GATEWAY_CALLER_CREDENTIALS_JSON`, opzionali `STAGING_RESEARCH_MODE`, `STAGING_DEFAULT_DAILY_AI_QUOTA` (5), `STAGING_DAILY_AI_BUDGET_TOTAL` (50).

## Differenze volute
Quote AI piu' basse. Il gateway puo' essere lo stesso di produzione (stesso tetto giornaliero condiviso) o uno dedicato (nuovo `infra/gcp` con altro `project_id`): decisione di Davide. Realm Keycloak separato.

## Uso
1. Crea in Coolify una risorsa Docker Compose dal file `docker-compose.staging.yml`, branch di prova, dominio distinto.
2. Imposta le variabili; deploy; controlla `/ready`.
3. Prova completa con un partecipante simulato (9.2#1): fuori da questa preparazione.
Non e' stato creato nulla su Coolify (serve il via di Davide).
