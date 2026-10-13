# Gateway AI su Cloud Run

Codice in `gateway/` (FastAPI, senza stato), infrastruttura in `infra/gcp`, client in `backend/app/core/gateway.py`.

- **Autenticazione**: il chiamante manda un ID token OIDC (`Authorization: Bearer`). Il gateway verifica firma, scadenza, `audience` (= URL del servizio) ed e-mail verificata nella lista `ALLOWED_CALLERS`. In piu' Cloud Run richiede `run.invoker` (solo il chiamante).
- **Fissati lato gateway**: modello (`VERTEX_MODEL`), token massimi (`MAX_OUTPUT_TOKENS`), lunghezza massima (`MAX_INPUT_CHARS`); il chiamante invia solo messaggi e temperatura (limitata a 0-1).
- **Registro dei token**: una riga JSON su stdout per richiesta (`event`, `caller`, `model`, `input_tokens`, `output_tokens`), raccolta da Cloud Logging.
- **Interruttore**: `AI_ENABLED=false` -> 503. **Tetto**: `DAILY_REQUEST_CAP` -> 429 (contatore in memoria, istanza massima 1).
- **App**: se `LLM_GATEWAY_URL` e' impostata il provider `vertex` chiama il gateway con ID token (`GATEWAY_CALLER_CREDENTIALS_JSON`, oppure ADC/metadata); altrimenti chiama Vertex direttamente (test locali).
- **Test**: `cd gateway && python -m pytest tests` (8) e `backend/tests/test_gateway.py` (4, gateway simulato con `httpx.MockTransport`).
- **Rotazione del segreto**: ricreare la chiave con `terraform apply -replace=google_service_account_key.caller[0] -var create_caller_key=true` (flusso con SI), aggiornare Coolify, poi eliminare la chiave vecchia.

## Pubblicazione dell'immagine (dopo il via)
```bash
IMG="$(terraform -chdir=infra/gcp output -raw artifact_registry_image_base):v1"
gcloud auth configure-docker europe-west4-docker.pkg.dev
docker build --platform linux/amd64 -t "$IMG" gateway/ && docker push "$IMG"
# poi plan/apply con -var gateway_image="$IMG"
```
