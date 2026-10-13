#!/usr/bin/env bash
# Backup PostgreSQL: pg_dump compresso, rotazione locale e copia fuori dal VPS.
# Variabili: PGHOST PGPORT PGUSER PGPASSWORD (o PGPASSFILE) PGDATABASE (oppure DATABASE_URL, scomposto in variabili PG*: la password non compare mai negli argomenti), BACKUP_DIR (default ./pg_backups),
#            BACKUP_KEEP (default 14), BACKUP_REMOTE (es. gs://bucket/pg  oppure  rclone:remote:cartella). Vuoto = nessuna copia remota (avviso).
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-./pg_backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$BACKUP_DIR/aidb_${stamp}.sql.gz"
tmp="$file.part"

if [[ -n "${DATABASE_URL:-}" ]]; then
  # La password NON va nella riga di comando (visibile con `ps`): si scompone l'URL in variabili PG*.
  eval "$(python3 - <<'PY'
import os, shlex
from urllib.parse import urlsplit, unquote
u = urlsplit(os.environ["DATABASE_URL"].replace("postgresql+psycopg2", "postgresql", 1))
for key, value in (("PGHOST", u.hostname), ("PGPORT", u.port), ("PGUSER", unquote(u.username or "")),
                   ("PGPASSWORD", unquote(u.password or "")), ("PGDATABASE", u.path.lstrip("/"))):
    if value:
        print(f"export {key}={shlex.quote(str(value))}")
PY
)"
  unset DATABASE_URL
fi
: "${PGDATABASE:?imposta PGDATABASE o DATABASE_URL}"
pg_dump --no-owner --no-privileges | gzip -9 > "$tmp"
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
