#!/usr/bin/env bash
# Controlla /health e /ready; se falliscono avvisa via webhook (JSON {"text": "..."}: Slack, Discord-compatibile, ntfy, ecc.).
#   APP_URL=https://aidbcreator.tecniaweb.it ALERT_WEBHOOK_URL=https://... scripts/ops_uptime_check.sh
# Codice di uscita 0 = tutto ok, 1 = problema. Pensato per cron o per un task pianificato di Coolify.
set -uo pipefail
: "${APP_URL:?imposta APP_URL}"
base="${APP_URL%/}"
problems=()
for path in /health /ready; do
  code="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$base$path" || true)"
  [[ "$code" == "200" ]] || problems+=("$path -> HTTP ${code:-000}")
done
if ((${#problems[@]} == 0)); then
  echo "OK $base"; exit 0
fi
msg="AI-DB-Creator GIU' ($base): ${problems[*]}"
echo "$msg" >&2
if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
  payload="$(printf '{"text":"%s"}' "${msg//\"/\'}")"
  curl -s -m 10 -X POST -H 'Content-Type: application/json' -d "$payload" "$ALERT_WEBHOOK_URL" >/dev/null || echo "Webhook non raggiungibile" >&2
else
  echo "ALERT_WEBHOOK_URL non impostata: nessun avviso inviato" >&2
fi
exit 1
