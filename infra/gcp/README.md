# Infrastruttura Google Cloud (Vertex AI)

Crea un progetto nuovo e dedicato, collega la fatturazione, abilita le API, prepara un service account
con il solo ruolo `aiplatform.user` e imposta gli avvisi di spesa. Tutto passa da Terraform.

## Prima esecuzione (solo dopo il via esplicito di Davide)

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars   # inserisci l'ID dell'account di fatturazione
gcloud auth application-default login
terraform init
terraform plan -out plan.tfplan                # si legge, non si applica alla cieca
terraform apply plan.tfplan
```

Per ottenere la chiave del service account da mettere in Coolify:
`terraform apply -var create_service_account_key=true` poi
`terraform output -raw service_account_key_json` (finisce solo nello stato locale, ignorato da git).

## Su Coolify

`VERTEX_PROJECT` = output `project_id`, `VERTEX_LOCATION` = `europe-west4`, `VERTEX_MODEL` = `gemini-2.5-flash-lite`,
`VERTEX_CREDENTIALS_JSON` = chiave JSON, `LLM_PROVIDER` = `vertex`.

## Nota sul gateway

Il piano prevedeva un gateway su Cloud Run davanti a Vertex. In questa fase l'app chiama Vertex direttamente
con il service account a privilegio minimo e le quote dell'app (`/api/admin`) fanno da freno. Il gateway si aggiunge
in seguito senza cambiare il resto: l'app legge solo `VERTEX_*`.
