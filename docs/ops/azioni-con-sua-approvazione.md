# Azioni che richiedono il via esplicito di Davide

Gli agenti preparano, non eseguono. Le azioni qui sotto partono solo dopo un messaggio di Davide che le nomina.
Ogni azione eseguita va poi scritta in `registro-modifiche.md`.

| Categoria | Azione | Cosa serve da Davide |
|---|---|---|
| Apply | `terraform apply` in `infra/gcp/bootstrap` e in `infra/gcp` | piano letto + "SI" digitato (`scripts/ops_terraform_flow.sh`) |
| Fatturazione | collegare l'account di fatturazione, creare budget, cambiare soglie | ID dell'account (`gcloud billing accounts list`), importo mensile |
| IAM | creare/cambiare service account, ruoli, `run.invoker`, chiavi JSON | conferma dei ruoli (solo `aiplatform.user` al gateway, `run.invoker` al chiamante) |
| Segreti | creare chiavi, incollare segreti in Coolify, ruotarli | esecuzione da lui o presenza durante l'inserimento |
| Eliminazioni | `terraform destroy`, cancellare bucket stato, progetto, volumi, database, backup | conferma per iscritto; il progetto ha `deletion_policy = PREVENT` |
| Deploy | build/push del gateway, deploy su Coolify (app, worker, redis, staging) | via per ambiente |
| DNS | record `aidbcreator.tecniaweb.it` -> 89.168.29.98 | lo crea lui sul provider del dominio |
| Dominio/HTTPS | associare il dominio in Coolify, certificati | dopo il DNS |
| Keycloak | cambiare realm, redirect URI, `sslRequired`, ruoli admin | via per ambiente |
| SonarQube | token e URL (preferibilmente HTTPS) | `SONAR_TOKEN`, `SONAR_HOST_URL` |
| Spegnimento AI | `scripts/ops_gateway_off.sh off|on` | via (e' un apply) |
| Backup/restore | schedulare il backup, scegliere la destinazione remota, ripristino di prova | destinazione (bucket/rclone) e credenziali |
| Dati | scrivere su database di produzione, eseguire `ops_create_app_user.sql` | via |

Non richiedono via: lettura del repository, test locali, `terraform validate`/`fmt`, scrittura di file nel repo (senza commit).
Il commit lo decide chi integra.
