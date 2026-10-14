# Due deploy su Coolify: prodotto e ricerca

Stato: **preparato, nulla eseguito**. Servono il via di Davide e l'accesso a Coolify e Cloudflare.

## Idea
Lo stesso `docker-compose.coolify.yml` e la stessa immagine, in due risorse Coolify con variabili diverse. La differenza funzionale e' `RESEARCH_MODE` (strumenti di studio accesi o spenti).

| | Prodotto | Ricerca |
|---|---|---|
| Dominio | `aidb.paas.tecniaweb.it` | `aidb-research.paas.tecniaweb.it` |
| `RESEARCH_MODE` | `false` | `true` |
| `KEYCLOAK_CLIENT_ID` | `aidbcreator-app` | `aidbcreator-research` |
| Postgres e Redis | propri, nel compose della risorsa | propri, nel compose della risorsa |

Variabili complete: `coolify/prodotto.env.example` e `coolify/ricerca.env.example`.

## Perche' due client Keycloak
All'avvio `keycloak_setup.py` riallinea il client del realm e imposta `redirectUris = [APP_PUBLIC_URL/*]`. Con lo stesso `KEYCLOAK_CLIENT_ID` i due deploy si sovrascriverebbero a vicenda l'indirizzo a ogni riavvio, e uno dei due perderebbe il login. Con client diversi nello stesso realm ogni deploy tiene il suo, e gli utenti restano gli stessi.

## Postgres e Redis nel compose
Ogni deploy ha il suo Postgres e il suo Redis nel compose, con password generate da Coolify (variabili `SERVICE_PASSWORD_*`): i dati dello studio non si mescolano a quelli dei clienti e nessun segreto va incollato. I segreti condivisi (`KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD`, `VERTEX_CREDENTIALS_JSON`) si creano una sola volta come Shared Variables del team e si richiamano con `{{team.NOME}}`.

## Domini e Cloudflare (zona tecniaweb.it)
Due record `A` verso `89.168.29.98`, entrambi con nuvola **grigia** (solo DNS): `paas` e `*.paas`. Il wildcard fa arrivare al server qualsiasi sottodominio di `paas`; per ogni dominio assegnato a una risorsa Coolify (Traefik) ottiene da solo il certificato Let's Encrypt, senza altri record.

| Uso | Dominio |
|---|---|
| Keycloak comune | invariato (sslip.io, HTTPS); `auth.paas.tecniaweb.it` opzionale |
| Prodotto | `aidb.paas.tecniaweb.it` |
| Ricerca | `aidb-research.paas.tecniaweb.it` |
| Pannello Coolify (opzionale, per ultimo) | `paas.tecniaweb.it` |

Con la nuvola arancione il certificato universale di Cloudflare non copre due livelli (`*.paas.tecniaweb.it`): lasciare grigia.

## Keycloak comune
Si usa il Keycloak gia' presente nei Services di Coolify, realm `aidbcreator`. Risponde gia' in HTTPS sul suo indirizzo sslip.io, usato da altre app: lo si lascia invariato e le due app lo usano come `KEYCLOAK_URL` (default del compose). `auth.paas.tecniaweb.it` si potra' aggiungere dopo.

## Ordine
1. Terraform: applicare `infra/gcp/local-dev` e creare la chiave di produzione (`vertex-diretto.md`).
2. Shared Variables del team in Coolify con i tre segreti.
3. DNS su Cloudflare (`paas` e `*.paas`).
4. Risorsa **prodotto**: repository e branch, compose `docker-compose.coolify.yml`, variabili di `prodotto.env.example`, dominio sul servizio `app`, deploy. Prova: `/ready` 200, registrazione, login, `/app/examples`.
5. Risorsa **ricerca**: uguale, con `ricerca.env.example`.
6. Keycloak: verificare che esistano `aidbcreator-app` e `aidbcreator-research` con i redirect corretti; togliere i vecchi indirizzi sslip.io.
7. Voci nel `registro-modifiche.md` per ogni passo.
