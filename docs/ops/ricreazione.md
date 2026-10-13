# Distruggi e ricrea da zero (da provare dopo il via di Davide)

Obiettivo: dimostrare che tutta l'infrastruttura si ricostruisce con Terraform, in un solo passaggio documentato.
Da eseguire una volta dopo il primo apply e registrare l'esito in `registro-modifiche.md`.

## Cosa si distrugge e cosa no
- `infra/gcp` (gateway, Artifact Registry, service account, segreti, budget): si puo' distruggere e ricreare. Il servizio Cloud Run ha `deletion_protection = false`.
- `infra/gcp/bootstrap` (progetto + bucket di stato): NON si distrugge nella prova. Il progetto ha `deletion_policy = PREVENT` e il bucket `force_destroy = false`.
- Le immagini in Artifact Registry vanno perse: dopo la ricreazione si pubblica di nuovo il gateway.
- Il segreto `gateway-caller-key` e la chiave del chiamante cambiano: si aggiorna `GATEWAY_CALLER_CREDENTIALS_JSON` in Coolify.

## Procedura (ognuna con il via di Davide)
1. Registra la riga nel registro. Spegni l'AI: `scripts/ops_gateway_off.sh off`.
2. Distruzione: `terraform -chdir=infra/gcp plan -destroy -out=plan.tfplan`, lettura, `scripts/ops_terraform_flow.sh apply infra/gcp` (digita SI).
3. Ricreazione: `scripts/ops_terraform_flow.sh plan infra/gcp -var create_caller_key=true`, lettura, `apply`.
4. Pubblica il gateway: `docker build -t "$(terraform -chdir=infra/gcp output -raw artifact_registry_image_base):v1" gateway/ && docker push ...`, poi `-var gateway_image=...:v1` con un nuovo plan/apply.
5. Copia `gateway_url` e la chiave del chiamante in Coolify (`LLM_GATEWAY_URL`, `GATEWAY_CALLER_CREDENTIALS_JSON`); riavvia app e worker.
6. Verifica: una chiamata AI di prova passa (200), una senza token ottiene 401, `/ready` dell'app e' 200.
7. Riaccendi l'AI se spenta e chiudi la riga del registro con l'esito e i tempi.

## Criterio di successo
Tutto rifatto senza interventi manuali sulla console GCP; tempo misurato; elenco dei passi manuali residui (immagine, segreti in Coolify).
