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
- Il compose di produzione ha i default sslip.io per `KEYCLOAK_URL` e `APP_PUBLIC_URL` vuoto: finche' non e' impostato, nessun redirect URI restrittivo (`["*"]`): da impostare prima del lancio pubblico.
