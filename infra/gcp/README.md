# Infrastruttura Google Cloud (gateway AI + Vertex)

Tutto passa da Terraform, mai dalla console. Nulla e' stato applicato. Ogni `apply` richiede il via di Davide
(`docs/ops/azioni-con-sua-approvazione.md`) e passa dal flusso `plan -> lettura -> SI -> apply`.

- `bootstrap/`: stato LOCALE; crea il progetto dedicato (`aidb-creator-<suffisso>`) e il bucket GCS versionato per lo stato.
- radice (`infra/gcp`): stato remoto nel bucket; API, Artifact Registry, service account (gateway: solo `aiplatform.user`; chiamante: solo `run.invoker`), servizio Cloud Run `aidb-gateway` (istanze 0..1), segreto della chiave del chiamante, budget con soglie.

## Prima esecuzione (solo dopo il via)
```bash
# 1. bootstrap (stato locale: conservalo fuori dal repo)
cd infra/gcp/bootstrap
cp terraform.tfvars.example terraform.tfvars        # billing_account_id
gcloud auth application-default login
terraform init
cd ../../..
scripts/ops_terraform_flow.sh plan  infra/gcp/bootstrap
scripts/ops_terraform_flow.sh apply infra/gcp/bootstrap
terraform -chdir=infra/gcp/bootstrap output          # project_id, tfstate_bucket

# 2. infrastruttura principale
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars        # project_id, billing_account_id, email avvisi
terraform init -backend-config="bucket=<tfstate_bucket>"
cd ../..
scripts/ops_terraform_flow.sh plan  infra/gcp
scripts/ops_terraform_flow.sh apply infra/gcp
```
Poi pubblica l'immagine del gateway e collega Coolify: `docs/ops/gateway.md`.
Chiave del chiamante: `plan infra/gcp -var create_caller_key=true`, poi `gcloud secrets versions access latest --secret=gateway-caller-key` (incolla in Coolify come `GATEWAY_CALLER_CREDENTIALS_JSON`).

## Su Coolify
`LLM_PROVIDER=vertex`, `LLM_GATEWAY_URL` = output `gateway_url`, `GATEWAY_CALLER_CREDENTIALS_JSON` = chiave del chiamante, `VERTEX_MODEL`.
Nessuna chiave Vertex fuori da GCP.

## Spegnimento, revisione, ricreazione
`docs/ops/spegnimento-gateway.md`, `docs/ops/terraform-review.md`, `docs/ops/ricreazione.md`.

## Validazione locale (senza toccare GCP)
```bash
for d in infra/gcp infra/gcp/bootstrap; do (cd $d && terraform init -backend=false && terraform validate); done
rm -f infra/gcp/.terraform.lock.hcl infra/gcp/bootstrap/.terraform.lock.hcl
```
