# Registro delle modifiche reali (Coolify e Google Cloud)

Ogni modifica che tocca un sistema vero (Coolify, Google Cloud, DNS, Keycloak di produzione) si scrive qui
**prima** di farla (riga con stato "da fare") e si chiude **subito dopo** (stato "fatto" o "annullato").
Nessun segreto in questo file: solo nomi di variabili, ID di risorse, link ai piani.

Regola: nessuna modifica a GCP fuori da Terraform, nemmeno dalla console. Il piano Terraform letto e approvato
da Davide e' l'allegato della riga.

## Modello di riga

| Campo | Contenuto |
|---|---|
| Data e ora (UTC) | 2026-01-01 12:00 |
| Sistema | Coolify / GCP / DNS / Keycloak |
| Cosa cambia | una frase |
| Perche' (task) | ID del piano, es. 2.6#3 |
| Chi l'ha chiesto / approvato | nome e riferimento al messaggio |
| Come | `terraform apply plan.tfplan` / schermata Coolify / comando |
| Piano o diff allegato | percorso o hash di `plan.tfplan` |
| Come si annulla | procedura di ritorno |
| Esito | fatto / annullato / parziale |
| Verifica dopo | cosa e' stato controllato (es. /ready 200) |

## Registro

| Data (UTC) | Sistema | Cosa cambia | Task | Approvato da | Come | Annullamento | Esito | Verifica |
|---|---|---|---|---|---|---|---|---|
| 2026-10-14 11:45 | GCP | Applicato `infra/gcp/local-dev`: service account `aidb-prod` (`aiplatform.user`), API budget e monitoring, canale email di avviso e budget mensile 5 EUR, poi chiave JSON di produzione in `.secrets/vertex-prod-sa.json` | vertex-diretto | Davide (chat, 2026-10-14) | `terraform apply` (6 + 2 risorse, 0 modifiche, 0 distruzioni) | `terraform destroy -target=google_service_account.prod` oppure eliminare la chiave | fatto | `gcloud iam service-accounts keys list`: 1 chiave utente su aidb-prod |
| 2026-10-14 08:25 | GCP | Nuovo progetto `aidbcreator-research-2026` (billing 01976E-58E7D6-376FBF), API Vertex AI, service account `aidb-runner` con `roles/aiplatform.user`, una chiave JSON locale in `.secrets/` (non versionata) | uso locale | Davide (richiesta in chat) | `gcloud`, poi importato in Terraform (`infra/gcp/local-dev`, apply 2026-10-14: 4 import, 5 aggiunte; chiave manuale sostituita da quella gestita) | eliminare la chiave con `gcloud iam service-accounts keys delete`, oppure `gcloud projects delete aidbcreator-research-2026` | fatto | chiamata di prova a Gemini dal container: ok |
