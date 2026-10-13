# SonarQube

Stato: configurazione pronta, **nessuna scansione eseguita** (manca il token).

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
