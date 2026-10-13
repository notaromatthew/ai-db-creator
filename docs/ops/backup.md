# PostgreSQL: persistenza, utente applicativo, backup e ripristino

Stato: script scritti e controllati con `bash -n`; shellcheck non e' installato. **Mai provati su un Postgres vero**: la prova di ripristino
(punto 4) e' obbligatoria prima di dichiarare il backup affidabile.

## 1. Volume persistente
Postgres non e' nel compose di produzione: e' una risorsa database di Coolify. In Coolify, sulla risorsa Postgres, controlla che
"Persistent Storage" sia attivo (volume su `/var/lib/postgresql/data`) e che non venga mai ricreato senza volume. Redis (nel compose) usa il volume `redis_data`.

## 2. Utente applicativo a privilegi minimi
```bash
psql "$ADMIN_DATABASE_URL" -v app_password="'$(openssl rand -hex 24)'" -f scripts/ops_create_app_user.sql
```
Crea `aidb_app` (login, non superuser, nessun CREATE su schema, solo SELECT/INSERT/UPDATE/DELETE e sequenze). Metti la password
in `DATABASE_URL` nei secrets di Coolify. Le migrazioni Alembic (DDL) si eseguono con l'utente amministratore al deploy: se l'app le
lancia all'avvio, serve un utente "migrator" con diritti DDL o concedere CREATE ad `aidb_app`: da decidere con Davide prima del via.

## 3. Backup
`scripts/ops_pg_backup.sh` fa `pg_dump` compresso (`gzip -9`), verifica il file, tiene gli ultimi `BACKUP_KEEP` (14) e copia fuori VPS.
Variabili: `DATABASE_URL` (oppure `PGHOST/PGUSER/PGPASSWORD/PGDATABASE`), `BACKUP_DIR`, `BACKUP_KEEP`,
`BACKUP_REMOTE` = `gs://bucket/cartella` (usa `gcloud storage cp`) oppure `rclone:remoto:cartella`.
Destinazione consigliata: un bucket GCS separato dallo stato Terraform, con ciclo di vita (es. 30 giorni) e account di servizio con solo
`roles/storage.objectCreator`. Non e' ancora creato: richiede il via di Davide (aggiunta al Terraform).

Pianificazione su Coolify: Scheduled Task sul servizio con `pg_dump` disponibile (o contenitore `postgres:16-alpine` con i client),
frequenza `0 3 * * *`, comando `/bin/sh scripts/ops_pg_backup.sh`. In alternativa cron sul VPS:
`0 3 * * * cd /opt/aidb && DATABASE_URL=... BACKUP_REMOTE=gs://... scripts/ops_pg_backup.sh >> /var/log/aidb_backup.log 2>&1`.

## 4. Prova di ripristino (da fare)
```bash
PGHOST=... PGUSER=... PGPASSWORD=... scripts/ops_pg_restore_test.sh pg_backups/aidb_<data>.sql.gz users projects
```
Crea un database temporaneo, carica il dump, stampa i conteggi per tabella (e quelli del database vivo se `PGDATABASE` e' impostata), poi lo elimina.
Esito `OK` solo se le tabelle esistono. Ripetere ogni mese; registrare data ed esito in `registro-modifiche.md`.

## Cosa resta da provare
Esecuzione reale di backup, copia remota, ripristino, e dell'utente `aidb_app` con l'app; schedulazione su Coolify; strategia Alembic (3.2#2, fuori perimetro).
