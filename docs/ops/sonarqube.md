# SonarQube

Stato: scansioni eseguite sul server SonarQube (la prima il 2026-10-13). Il progetto `ai-db-creator` esiste; host e token stanno in `.sonar.env` (ignorato da git).

## Cosa serve da Davide
- `SONAR_TOKEN` (token utente o di progetto, scope "Execute Analysis"), creato in SonarQube > My Account > Security. Mai nel repository.
- `SONAR_HOST_URL` del server. Verificare l'accesso (`curl -s $SONAR_HOST_URL/api/system/status`).
- Conferma che il progetto `ai-db-creator` esista, o permesso di crearlo.

## Esecuzione
```bash
export SONAR_HOST_URL=...   # e SONAR_TOKEN=... dall'ambiente / gestore di segreti
scripts/sonar_scan.sh
```
Rifiuta di partire se mancano le variabili. Genera `backend/coverage.xml` (pytest-cov) e, se `@vitest/coverage-v8` e' installato, `frontend/coverage/lcov.info`; poi lancia `sonar-scanner` (o l'immagine Docker) con `qualitygate.wait=true`.
Lo script storico `scripts/run_sonar_scan.sh` ha host e utente fissi nel file e autentica con utente/password invece del token: non usarlo, va sostituito da `sonar_scan.sh`.

## Quality gate
- Base: **Sonar way**.
- Condizione aggiuntiva: copertura sul **nuovo codice >= 80%** (D7).
- Punti di controllo G1, G2, G3, G4: zero bug e zero vulnerabilita' bloccanti/critiche; correggere i problemi prima di chiudere ciascun punto (0.3#4).
- Copertura backend oggi circa 66% sul totale (dato dal piano); il gate guarda il codice nuovo.
- Il frontend non ha ancora la dipendenza di copertura: `npm i -D @vitest/coverage-v8` (modifica a `package.json`, fuori perimetro di questa preparazione).

## Rischio HTTP
Il server risponde in HTTP: il token viaggia in chiaro e puo' essere intercettato (e con esso l'accesso in scrittura al progetto). Fino a che non c'e' HTTPS (reverse proxy Coolify con certificato, vedi `dominio-https.md`):
usare un token a scadenza breve e con permessi minimi, scansionare solo da rete fidata/VPN, revocarlo dopo ogni uso. `sonar_scan.sh` stampa un avviso se l'URL e' `http://`.

## Scansione da un worktree git con Docker (verificata 2026-10-14)
`scripts/sonar_scan.sh` presuppone Python e sonar-scanner sul Mac. Da un worktree, con Docker:
1. Copertura backend, montando il worktree in `/usr/src` (i percorsi in `coverage.xml` devono coincidere con quelli dello scanner): `docker run --rm --user root -v "$PWD":/usr/src -w /usr/src/backend <immagine app> sh -c 'pip install pytest-cov && python -m pytest tests -q --cov=app --cov-report=xml:coverage.xml'`.
2. Copertura frontend con `vitest run --coverage --coverage.reporter=lcov`; in `lcov.info` prefissare i percorsi con `frontend/` (`sed 's#^SF:#SF:frontend/#'`).
3. Scanner: `docker run --rm --env-file .sonar.env -v "$PWD":/usr/src -v <repo>/.git:<repo>/.git:ro sonarsource/sonar-scanner-cli -Dsonar.scm.disabled=true -Dsonar.qualitygate.wait=true`. Il `.git` va montato allo stesso percorso perche' il worktree lo referenzia. **`-Dsonar.scm.disabled=true` e' necessario**: senza, lo scanner in un worktree non trova file da analizzare e il quality gate risulta "passed" con zero righe analizzate (risultato vuoto, da non fidarsi). Controlla sempre `ncloc` nelle misure.
