#!/usr/bin/env bash
# Spegne (off) o riaccende (on) il gateway AI cambiando ai_enabled in Terraform, con il flusso piano -> SI -> apply.
#   scripts/ops_gateway_off.sh off|on
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dir="${INFRA_DIR:-$here/../infra/gcp}"
case "${1:-}" in
  off) val=false ;;
  on)  val=true ;;
  *) echo "Uso: $0 off|on" >&2; exit 2 ;;
esac
"$here/ops_terraform_flow.sh" plan "$dir" -var "ai_enabled=$val"
"$here/ops_terraform_flow.sh" apply "$dir"
