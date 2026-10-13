# Revisione di sicurezza del Terraform

Stato: `terraform validate` e `terraform fmt -check` passano in `infra/gcp` e `infra/gcp/bootstrap`
(provider google ~> 6.0). La revisione del piano (`terraform plan`) la fa un agente diverso da chi ha scritto
il codice, dopo il via di Davide: il piano non e' mai stato eseguito.

## Scansione automatica
`tfsec` non e' installato sul Mac. E' stato eseguito `checkov` (installato temporaneamente in un venv, poi rimosso):
9 controlli passati, 4 falliti.

| Controllo | Esito | Decisione |
|---|---|---|
| CKV_GCP_27 rete "default" nel progetto | corretto: `auto_create_network = false` | chiuso |
| CKV_GCP_62 log di accesso del bucket | accettato: bucket di stato, accesso solo di Davide, versionato | rivalutare se serve audit |
| CKV_GCP_84 chiave CMEK per Artifact Registry | accettato: chiavi gestite da Google, nessuna CMEK per costo/complessita' | |
| CKV2_GCP_5 Cloud Audit Logging | accettato: i log di Admin Activity sono sempre attivi; i Data Access non servono | |

Ripetere con: `pip install checkov && checkov -d infra/gcp --framework terraform --compact --quiet`
oppure `tfsec infra/gcp` se installato.

## Checklist manuale (da spuntare prima di ogni apply)
- [ ] Nessun segreto nei file `.tf`, `.tfvars.example`, README: `grep -rniE "private_key|password|secret_data *= *\"|AIza" infra/` non trova valori.
- [ ] `terraform.tfvars`, `*.tfstate*`, `*.tfplan`, `.terraform/` sono in `.gitignore` e `git status` non li mostra.
- [ ] Stato remoto: backend `gcs` con bucket passato a `-backend-config`; lo stato di `bootstrap/` e' locale e fuori dal repo (copia in luogo sicuro).
- [ ] Ruoli minimi: gateway = solo `roles/aiplatform.user`; chiamante = solo `roles/run.invoker` sul servizio del gateway; nessun `owner`/`editor`; nessun `allUsers`/`allAuthenticatedUsers`.
- [ ] Il servizio Cloud Run non ha `invoker_iam_disabled` e richiede autenticazione.
- [ ] Il gateway ha `min_instance_count = 0`, `max_instance_count = 1`.
- [ ] Bucket di stato: versioning acceso, accesso uniforme, `public_access_prevention = enforced`.
- [ ] Progetto con `deletion_policy = "PREVENT"`.
- [ ] La chiave JSON del chiamante si crea solo con `create_caller_key = true`, e finisce in Secret Manager e nello stato (che e' privato).
- [ ] Il piano non contiene distruzioni inattese (`-/+` o `-` su progetto, bucket, segreti).
- [ ] Il piano e' stato letto da un agente diverso dall'autore e da Davide.
