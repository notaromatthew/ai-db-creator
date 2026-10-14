# Due deploy su Coolify: prodotto e ricerca

Stato: **preparato, nulla eseguito**. Servono il via di Davide e l'accesso a Coolify e Cloudflare.

## Idea
Lo stesso `docker-compose.coolify.yml` e la stessa immagine, in due risorse Coolify con variabili diverse. La differenza funzionale e' `RESEARCH_MODE` (strumenti di studio accesi o spenti).

| | Prodotto | Ricerca |
|---|---|---|
| Dominio | `aidbcreator.tecniaweb.it` | `aidbcreator-ricerca.tecniaweb.it` |
| `RESEARCH_MODE` | `false` | `true` |
| `KEYCLOAK_CLIENT_ID` | `aidbcreator-app` | `aidbcreator-research` |
| Database | `aidb_prodotto` | `aidb_ricerca` |
| Redis | proprio (nella risorsa) | proprio (nella risorsa) |

Variabili complete: `coolify/prodotto.env.example` e `coolify/ricerca.env.example`.

## Perche' due client Keycloak
All'avvio `keycloak_setup.py` riallinea il client del realm e imposta `redirectUris = [APP_PUBLIC_URL/*]`. Con lo stesso `KEYCLOAK_CLIENT_ID` i due deploy si sovrascriverebbero a vicenda l'indirizzo a ogni riavvio, e uno dei due perderebbe il login. Con client diversi nello stesso realm ogni deploy tiene il suo, e gli utenti restano gli stessi.

## Perche' due database
I dati dello studio non devono mescolarsi a quelli dei clienti. Un solo Postgres su Coolify con due database (`aidb_prodotto`, `aidb_ricerca`) e due utenti costa come uno solo.

## Cloudflare (dominio tecniaweb.it)
Record da creare (non posso farlo io):
- `A aidbcreator -> 89.168.29.98`
- `A aidbcreator-ricerca -> 89.168.29.98`

Sottodomini a un solo livello, coperti dal certificato universale di Cloudflare. Parti con la nuvola **grigia (solo DNS)** cosi' Coolify ottiene il certificato Let's Encrypt; poi, se vuoi il proxy, passa a nuvola arancione con SSL/TLS in modalita' **Full (strict)**. Con il proxy attivo i caricamenti sono limitati a 100 MB per richiesta (piano gratuito).

## Ordine
1. Terraform: applicare `infra/gcp/local-dev` e creare la chiave di produzione (`vertex-diretto.md`).
2. Postgres in Coolify: due database e due utenti.
3. DNS su Cloudflare (due record).
4. Risorsa **prodotto**: repository e branch, compose `docker-compose.coolify.yml`, variabili di `prodotto.env.example`, dominio sul servizio `app`, deploy. Prova: `/ready` 200, registrazione, login, `/app/examples`.
5. Risorsa **ricerca**: uguale, con `ricerca.env.example`.
6. Keycloak: verificare che esistano `aidbcreator-app` e `aidbcreator-research` con i redirect corretti; togliere i vecchi indirizzi sslip.io.
7. Voci nel `registro-modifiche.md` per ogni passo.
