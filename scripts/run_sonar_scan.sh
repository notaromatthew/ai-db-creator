#!/usr/bin/env bash
set -e

SONAR_HOST="http://o4sn9bs961jvxn32hs18a81p.89.168.29.98.sslip.io:9000"
SONAR_USER="admin"
SONAR_PASS="${SONAR_PASSWORD:-}"


echo "Checking SonarQube server at ${SONAR_HOST}..."
curl -s -u "${SONAR_USER}:${SONAR_PASS}" "${SONAR_HOST}/api/system/status" || echo "SonarQube server ping complete."

echo "Running SonarQube Scanner..."
if command -v sonar-scanner &> /dev/null; then
    sonar-scanner \
        -Dsonar.host.url="${SONAR_HOST}" \
        -Dsonar.login="${SONAR_USER}" \
        -Dsonar.password="${SONAR_PASS}"
else
    echo "sonar-scanner CLI non trovato in locale. Puoi eseguire la scansione tramite Docker:"
    echo "docker run --rm -v \"\$(pwd):/usr/src\" sonarsource/sonar-scanner-cli -Dsonar.host.url=\"${SONAR_HOST}\" -Dsonar.login=\"${SONAR_USER}\" -Dsonar.password=\"${SONAR_PASS}\""
fi
