# Dominio e HTTPS

Nulla di quanto sotto e' stato fatto: serve il via di Davide (DNS, Coolify, Keycloak).

## Obiettivo
`https://aidbcreator.tecniaweb.it` per landing (`/`, `/en/`) e software (`/app`, `/app/shared/:token`), un host separato per Keycloak, certificati automatici (Let's Encrypt via Coolify/Traefik).

## Procedura definitiva
1. **DNS (Davide, 4.3#0)**: record `A aidbcreator.tecniaweb.it -> 89.168.29.98`; per Keycloak un secondo record (es. `A auth.aidbcreator.tecniaweb.it -> 89.168.29.98`). TTL basso (300) per la prova. Verifica con `dig +short aidbcreator.tecniaweb.it`.
2. **Coolify**: nella risorsa app, campo Domains = `https://aidbcreator.tecniaweb.it`; Coolify richiede il certificato appena il DNS risponde (porte 80/443 aperte). Stesso per Keycloak.
3. **Variabili** (secrets di Coolify; nel compose esistono gia'):
   - `APP_PUBLIC_URL=https://aidbcreator.tecniaweb.it` (senza slash finale)
   - `KEYCLOAK_URL=https://auth.aidbcreator.tecniaweb.it`
   Ridistribuisci app e worker.
4. **Redirect URI Keycloak**: `keycloak_setup.py` imposta `redirectUris = ["<APP_PUBLIC_URL>/*"]`, che copre `/app` e `/app/shared/*`; verifica nel client `aidbcreator-app` che compaia `https://aidbcreator.tecniaweb.it/*` e Web Origins `https://aidbcreator.tecniaweb.it`. Rimuovi i vecchi URI sslip.io dopo il passaggio. Il frontend (`VITE_KEYCLOAK_URL`, argomento di build) va ricostruito con il nuovo URL.
5. **Prova**: `curl -I https://aidbcreator.tecniaweb.it/ready` -> 200; login da `/app`; ritorno su `/app`.

## Opzione provvisoria: indirizzo generato da Coolify (D4, 4.3#2-#4)
- Si usa l'indirizzo `*.sslip.io` assegnato da Coolify, senza record DNS. Si tenta il certificato HTTPS anche li' (4.3#3): Let's Encrypt a volte rifiuta `sslip.io` per i limiti di richieste condivisi.
- **Se resta in HTTP**: Keycloak con `sslRequired: none` solo per questa fase (realm `aidbcreator`; oggi `keycloak_setup.py` imposta `external`), con avviso esplicito agli utenti. Rischi: password in chiaro; e una pagina HTTPS non puo' chiamare Keycloak in HTTP (contenuto misto), quindi app e Keycloak devono essere entrambi HTTP o entrambi HTTPS.
- Il passaggio al dominio TecnIA cambia solo `APP_PUBLIC_URL`, `KEYCLOAK_URL`, redirect URI e la build del frontend; poi `sslRequired` torna a `external`.
- Il compose di produzione ha i default sslip.io per `KEYCLOAK_URL`; `APP_PUBLIC_URL` e' obbligatorio (`${APP_PUBLIC_URL:?...}`: il deploy si ferma se manca). Anche a livello applicativo `keycloak_setup.py` rifiuta di creare o sincronizzare il client senza `APP_PUBLIC_URL` (errore nel log, nessuna chiamata a Keycloak) e ammette `redirectUris=["*"]` solo se `ENVIRONMENT`/`APP_ENV` e' `development` o `test` (sviluppo locale).
- Verifica email: il realm imposta `verifyEmail` (variabile `KEYCLOAK_VERIFY_EMAIL`, default `true`; richiede SMTP configurato nel realm). Il ruolo admin e' assegnato a `FIRST_ADMIN_EMAIL` solo se l'utente ha `emailVerified` true, per evitare che qualcuno si registri con l'email dell'admin prima del titolare.

## Altre variabili introdotte dal rafforzamento
- `STUDY_ACCOUNT_SALT`: sale dell'HMAC che limita lo studio a una iscrizione per account (vedi `docs/migrazioni.md`).
- `KEYCLOAK_ISSUER` (facoltativa): issuer atteso del token; di default `{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}`. Da impostare solo se il backend raggiunge Keycloak con un URL interno diverso da quello pubblico.
- `KEYCLOAK_CHECK_CLIENT` (default `true`): il token deve avere `azp` uguale a `KEYCLOAK_CLIENT_ID` oppure tra le `aud`.
- `TASK_BINDING_SECRET` (facoltativa): chiave dell'etichetta che lega i task asincroni a chi li ha avviati.
- Le credenziali admin di Keycloak stanno solo sul servizio `app`: `docs/ops/keycloak-service-account.md`.
