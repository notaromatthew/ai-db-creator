#!/usr/bin/env bash
# Backup PostgreSQL: pg_dump compresso, rotazione locale e copia fuori dal VPS.
# Variabili: PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE (oppure DATABASE_URL), BACKUP_DIR (default ./pg_backups),
#            BACKUP_KEEP (default 14), BACKUP_REMOTE (es. gs://bucket/pg  oppure  rclone:remote:cartella). Vuoto = nessuna copia remota (avviso).
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-./pg_backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$BACKUP_DIR/aidb_${stamp}.sql.gz"
tmp="$file.part"

if [[ -n "${DATABASE_URL:-}" ]]; then
  pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$tmp"
else
  : "${PGDATABASE:?imposta PGDATABASE o DATABASE_URL}"
  pg_dump --no-owner --no-privileges | gzip -9 > "$tmp"
fi
gzip -t "$tmp"
[[ "$(stat -c %s "$tmp" 2>/dev/null || stat -f %z "$tmp")" -gt 200 ]] || { echo "Backup sospetto (troppo piccolo)" >&2; rm -f "$tmp"; exit 1; }
mv "$tmp" "$file"
echo "Backup creato: $file"

# Rotazione: tieni gli ultimi BACKUP_KEEP
ls -1t "$BACKUP_DIR"/aidb_*.sql.gz 2>/dev/null | tail -n +"$((BACKUP_KEEP + 1))" | while read -r old; do rm -f -- "$old"; done

# Copia fuori VPS
remote="${BACKUP_REMOTE:-}"
if [[ -z "$remote" ]]; then
  echo "ATTENZIONE: BACKUP_REMOTE non impostata, nessuna copia fuori dal VPS." >&2
elif [[ "$remote" == gs://* ]]; then
  gcloud storage cp "$file" "${remote%/}/" || gsutil cp "$file" "${remote%/}/"
elif [[ "$remote" == rclone:* ]]; then
  rclone copy "$file" "${remote#rclone:}"
else
  echo "BACKUP_REMOTE non riconosciuta: usa gs://... oppure rclone:remote:path" >&2; exit 1
fi
echo "Copia remota completata"
