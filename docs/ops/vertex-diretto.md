# Vertex AI diretto (produzione a costo minimo)

Stato: **preparato, nulla applicato**. Sostituisce il gateway Cloud Run (`gateway.md`, ~50 dollari al mese per l'istanza sempre accesa) quando il costo fisso non e' accettabile. Il gateway resta nel repository come alternativa piu' isolata.

## Come funziona
L'app su Coolify usa `LLM_PROVIDER=vertex` e chiama Vertex AI con il service account `aidb-prod` (solo `roles/aiplatform.user`). `LLM_GATEWAY_URL` e' vuoto, quindi il gateway e' spento. Il JSON del service account sta solo nei secrets di Coolify (`VERTEX_CREDENTIALS_JSON`).

## Costo
- Infrastruttura: nessuna risorsa a pagamento oltre al server Coolify esistente.
- Vertex: a consumo. `gemini-2.5-flash-lite` costa circa 0,07 centesimi di dollaro per richiesta tipica (stima, da verificare sui prezzi di Google).
- Tetti: `DAILY_AI_BUDGET_TOTAL` (150 al giorno di default nel compose), `DEFAULT_DAILY_AI_QUOTA` (10 per utente), `VERTEX_MAX_OUTPUT_TOKENS` (2048), `VERTEX_ALLOWED_MODELS` (senza Pro).

## Terraform (`infra/gcp/local-dev`)
Piano preparato: service account `aidb-prod`, ruolo, budget mensile (default 5 euro, solo avvisi) e API. La chiave di produzione si crea solo con `create_prod_key=true` e finisce in `.secrets/vertex-prod-sa.json` (ignorato da git) e nello stato locale di Terraform (non cifrato: custodiscilo fuori dal repo).
```bash
cd infra/gcp/local-dev
terraform plan -out=plan.tfplan                      # lettura
terraform apply plan.tfplan                          # dopo il tuo via
terraform plan -var create_prod_key=true -out=key.tfplan   # poi apply, per creare la chiave
```
Per ricevere gli avvisi sull'email: `-var budget_alert_email=...`.

## Da fare a mano in GCP (non e' in Terraform)
1. Quota Vertex: Quotas & System Limits, richieste al minuto per il modello usato, a un valore basso. E' il freno vero alla spesa.
2. Incollare il contenuto di `.secrets/vertex-prod-sa.json` in Coolify come secret `VERTEX_CREDENTIALS_JSON`.

## Rotazione e revoca
- Ruotare: `terraform apply -replace='google_service_account_key.prod[0]' -var create_prod_key=true`, aggiornare il secret, poi eliminare la vecchia chiave.
- Revocare: eliminare la chiave (`gcloud iam service-accounts keys delete ...`) oppure `terraform destroy -target=google_service_account.prod`.

## Rischio da accettare
L'app possiede una chiave: se trapela, qualcuno puo' spendere sul progetto fino alla quota Vertex. Per questo: ruolo minimo, quota bassa, budget con avvisi, nessun modello Pro.
