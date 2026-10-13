#!/usr/bin/env bash
# Flusso fisso Terraform: plan -> lettura -> conferma esplicita "SI" -> apply.
#   scripts/ops_terraform_flow.sh plan  <cartella> [argomenti terraform plan...]
#   scripts/ops_terraform_flow.sh apply <cartella>
# Rifiuta apply senza un plan file recente e senza che si digiti SI. Non esiste modo di saltare i passaggi.
set -euo pipefail

MAX_AGE_SECONDS="${PLAN_MAX_AGE_SECONDS:-3600}"
TF="${TERRAFORM_BIN:-terraform}"
cmd="${1:-}"; dir="${2:-}"
if [[ -z "$cmd" || -z "$dir" || ! -d "$dir" ]]; then
  echo "Uso: $0 plan|apply <cartella-terraform> [argomenti plan]" >&2; exit 2
fi
shift 2
PLAN_FILE="$dir/plan.tfplan"

case "$cmd" in
  plan)
    "$TF" -chdir="$dir" plan -input=false -out=plan.tfplan "$@"
    echo
    echo "=== Piano salvato in $PLAN_FILE. Leggilo, poi: $0 apply $dir ==="
    ;;
  apply)
    [[ -f "$PLAN_FILE" ]] || { echo "RIFIUTATO: manca $PLAN_FILE. Esegui prima '$0 plan $dir'." >&2; exit 1; }
    age=$(( $(date +%s) - $(stat -c %Y "$PLAN_FILE" 2>/dev/null || stat -f %m "$PLAN_FILE") ))
    if (( age > MAX_AGE_SECONDS )); then
      echo "RIFIUTATO: il piano ha ${age}s (max ${MAX_AGE_SECONDS}s). Rifallo con 'plan'." >&2; exit 1
    fi
    [[ -t 0 ]] || { echo "RIFIUTATO: serve un terminale interattivo per la conferma." >&2; exit 1; }
    "$TF" -chdir="$dir" show -no-color plan.tfplan
    echo
    echo "Stai per APPLICARE il piano qui sopra su Google Cloud."
    read -r -p 'Per procedere digita esattamente SI: ' answer
    [[ "$answer" == "SI" ]] || { echo "Annullato: risposta diversa da SI." >&2; exit 1; }
    "$TF" -chdir="$dir" apply -input=false plan.tfplan
    rm -f "$PLAN_FILE"
    echo "Apply completato. Registra la modifica in docs/ops/registro-modifiche.md"
    ;;
  *) echo "Comando sconosciuto: $cmd" >&2; exit 2 ;;
esac
