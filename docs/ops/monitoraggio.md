# Monitoraggio minimo e log

## Uptime
`/health` (processo vivo) e `/ready` (database raggiungibile; 503 se no) sono gli endpoint da controllare.

### Script
```bash
APP_URL=https://aidbcreator.tecniaweb.it ALERT_WEBHOOK_URL=https://... scripts/ops_uptime_check.sh
```
Esce con 1 e manda `{"text": "..."}` al webhook se uno dei due non risponde 200. Pianificazione: Scheduled Task di Coolify
ogni 5 minuti (`*/5 * * * *`) oppure cron. Meglio eseguirlo da una macchina diversa dal VPS, altrimenti non avvisa quando il VPS e' giu'.

### Alternative esterne (consigliate come primo livello)
- **UptimeRobot** (piano gratuito): monitor HTTP(s) su `<APP_URL>/health` e su `<APP_URL>/ready`, intervallo 5 minuti, contatto email/Telegram.
- **Coolify**: nella risorsa, scheda Health Check (`/ready`, porta 8000); il compose ha gia' un healthcheck su `/ready`. Notifiche Coolify (Email/Telegram/Discord) su deployment e contenitori non sani.

## Log in un punto solo
Coolify raccoglie stdout/stderr di ogni contenitore (scheda Logs del servizio; `docker logs` sul VPS). Il gateway scrive eventi JSON su stdout
(Cloud Logging li raccoglie in automatico: filtro `resource.type="cloud_run_revision"`, campi `event`, `input_tokens`, `output_tokens`).

### Verifica di `backend/app/utils/logger.py` (NON modificato)
Il logger scrive su stderr in formato testo a colori e **anche su file** `logs/app_{time}.log` (rotazione giornaliera, 7 giorni).
Quindi non e' ne' solo-stdout ne' JSON. In produzione i file finiscono nel filesystem del contenitore (non persistente, non letti da Coolify) e
usano spazio. Modifica proposta (da fare da chi ha il file): aggiungere `if os.getenv("LOG_TO_FILE") == "1"` attorno al secondo `logger.add`
e `serialize=True` sul sink stderr quando `LOG_JSON=1`. Fino ad allora i log "veri" sono quelli su stderr raccolti da Coolify.
