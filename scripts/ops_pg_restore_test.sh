#!/usr/bin/env bash
# Prova di ripristino: carica un backup in un database TEMPORANEO, confronta i conteggi, poi lo elimina.
#   scripts/ops_pg_restore_test.sh <file.sql.gz> [tabella ...]
# Richiede PGHOST PGPORT PGUSER PGPASSWORD con diritto CREATEDB. Non tocca il database di produzione.
set -euo pipefail
file="${1:-}"; shift || true
[[ -f "$file" ]] || { echo "Uso: $0 <file.sql.gz> [tabelle]" >&2; exit 2; }
tables=("$@"); [[ ${#tables[@]} -gt 0 ]] || tables=(users projects)
tmpdb="restore_test_$(date +%s)"
admin_db="${PGMAINT_DB:-postgres}"
cleanup() { psql -d "$admin_db" -qc "DROP DATABASE IF EXISTS \"$tmpdb\"" >/dev/null 2>&1 || true; }
trap cleanup EXIT

psql -d "$admin_db" -qc "CREATE DATABASE \"$tmpdb\""
gunzip -c "$file" | psql -d "$tmpdb" -q -v ON_ERROR_STOP=1 >/dev/null
echo "Ripristino in $tmpdb riuscito. Conteggi:"
fail=0
for t in "${tables[@]}"; do
  n="$(psql -d "$tmpdb" -Atc "SELECT count(*) FROM \"$t\"" 2>/dev/null || echo ERR)"
  echo "  $t: $n"
  [[ "$n" == "ERR" ]] && fail=1
  if [[ -n "${PGDATABASE:-}" && "$n" != "ERR" ]]; then
    live="$(psql -d "$PGDATABASE" -Atc "SELECT count(*) FROM \"$t\"" 2>/dev/null || echo "?")"
    echo "    (database vivo: $live; il backup puo' essere piu' vecchio)"
  fi
done
[[ $fail -eq 0 ]] && echo "ESITO: OK" || { echo "ESITO: FALLITO (tabella mancante)" >&2; exit 1; }
