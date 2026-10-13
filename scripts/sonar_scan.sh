#!/usr/bin/env bash
# Scansione SonarQube. Richiede SONAR_TOKEN e SONAR_HOST_URL da ambiente (mai nel repo).
# Genera copertura backend (pytest-cov) e frontend (vitest coverage, se installato), poi lancia sonar-scanner.
set -euo pipefail
root0="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$root0/.sonar.env" ]]; then set -a; . "$root0/.sonar.env"; set +a; fi
: "${SONAR_TOKEN:?SONAR_TOKEN mancante: nessuna scansione}"
: "${SONAR_HOST_URL:?SONAR_HOST_URL mancante: nessuna scansione}"
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ "$SONAR_HOST_URL" == http://* ]]; then
  echo "ATTENZIONE: il server risponde in HTTP, il token viaggia in chiaro (docs/ops/sonarqube.md)." >&2
fi

echo "== Copertura backend =="
(cd backend && python -m pytest tests -q --cov=app --cov-report=xml:coverage.xml)

if [[ -x frontend/node_modules/.bin/vitest ]] && ls frontend/node_modules/@vitest/coverage-* >/dev/null 2>&1; then
  echo "== Copertura frontend =="
  (cd frontend && npx vitest run --coverage --coverage.reporter=lcov)
else
  echo "Copertura frontend saltata: installa @vitest/coverage-v8 (npm i -D @vitest/coverage-v8)" >&2
fi

echo "== sonar-scanner =="
if command -v sonar-scanner >/dev/null; then
  sonar-scanner -Dsonar.host.url="$SONAR_HOST_URL" -Dsonar.token="$SONAR_TOKEN" -Dsonar.qualitygate.wait=true
elif command -v docker >/dev/null; then
  docker run --rm -e SONAR_HOST_URL -e SONAR_TOKEN -v "$root:/usr/src" sonarsource/sonar-scanner-cli -Dsonar.qualitygate.wait=true
else
  echo "Ne' sonar-scanner ne' docker trovati." >&2; exit 1
fi
