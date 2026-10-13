# Credenziali Keycloak dell'app: dal bootstrap al service account

## Oggi
`KEYCLOAK_ADMIN_USER` e `KEYCLOAK_ADMIN_PASSWORD` (utente admin del realm `master`) servono **solo** a `keycloak_setup.py`, che all'avvio
crea/riallinea realm, client e ruolo admin. Nel compose di produzione (`docker-compose.coolify.yml`) sono impostate solo sul servizio
`app`; il `worker` Celery non le riceve. Se l'app e' compromessa, pero', queste credenziali danno il controllo di tutto Keycloak.

## Passaggio consigliato a un client service-account (non ancora implementato)
1. In Keycloak, nel realm `aidbcreator`, crea il client confidenziale `aidb-provisioner` con *Service accounts enabled* e senza flussi utente.
2. Assegna al suo service account solo i ruoli del client `realm-management`: `manage-clients`, `view-clients`, `manage-realm`
   (per la sincronizzazione delle impostazioni), `view-users` e `manage-users` (per assegnare il ruolo `aidb-admin`). Niente `realm-admin`.
3. Salva il secret nei secrets di Coolify (`KEYCLOAK_PROVISIONER_SECRET`) e in `keycloak_setup.py` ottieni il token con
   `grant_type=client_credentials` sul realm `aidbcreator` invece di `admin-cli` sul realm `master`.
   Il realm resta da creare una volta a mano (il service account vive dentro il realm).
4. Rimuovi `KEYCLOAK_ADMIN_USER/PASSWORD` dal servizio `app` e ruota la password dell'admin `master`.
5. Alternativa piu' stretta: esegui il bootstrap come job una tantum (non nell'app) e togli del tutto le credenziali dall'app.
