# Gateway AI su Cloud Run

Codice in `gateway/` (FastAPI, senza stato), infrastruttura in `infra/gcp`, client in `backend/app/core/gateway.py`.

- **Autenticazione**: il chiamante manda un ID token OIDC (`Authorization: Bearer`). Il gateway verifica firma, scadenza, `audience` (= URL del servizio) ed e-mail verificata nella lista `ALLOWED_CALLERS`. In piu' Cloud Run richiede `run.invoker` (solo il chiamante).
- **Fissati lato gateway**: modello (`VERTEX_MODEL`), token massimi (`MAX_OUTPUT_TOKENS`), lunghezza massima (`MAX_INPUT_CHARS`); il chiamante invia solo messaggi e temperatura (limitata a 0-1).
- **Registro dei token**: una riga JSON su stdout per richiesta (`event`, `caller`, `model`, `input_tokens`, `output_tokens`), raccolta da Cloud Logging.
- **Interruttore**: `AI_ENABLED=false` -> 503. **Tetto**: `DAILY_REQUEST_CAP` -> 429. Il contatore e' in memoria e vale **per istanza**: Cloud Run e' configurato con `min_instance_count = 1`, `max_instance_count = 1` e CPU sempre allocata (`cpu_idle = false`), cosi' i cold start non lo azzerano. Un deploy o un riavvio lo azzera comunque, quindi il tetto e' un freno di sicurezza: il limite vero di spesa e' la **quota Vertex AI** (Quotas & System Limits, richieste al minuto per il modello) da impostare in GCP, e il budget con avvisi. Costo dell'istanza sempre accesa: circa 1 vCPU / 512 MiB 24 ore su 24.
- **Immagini (OCR dei PDF scansionati)**: i messaggi possono avere parti `{type: text}` e `{type: image, mime_type, data}` (base64, solo `image/png|jpeg|webp`, solo nei messaggi utente), inoltrate a Vertex come `inlineData`. Limiti lato gateway: `MAX_IMAGE_BYTES` (4 MiB per immagine), `MAX_IMAGES_PER_REQUEST` (8), al massimo 8 parti per messaggio; il client li applica gia' prima dell'invio.
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
