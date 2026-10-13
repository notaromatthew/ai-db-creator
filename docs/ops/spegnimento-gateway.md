# Spegnimento del gateway oltre il tetto (D2)

## Scelta
Tre livelli, dal piu' automatico al piu' manuale:

1. **Tetto giornaliero nel gateway** (`daily_request_cap`, default 500 richieste UTC/giorno): automatico, nessun costo oltre il tetto.
   Il contatore e' in memoria, per questo Cloud Run e' configurato con 1 sola istanza massima. Un riavvio azzera il contatore del giorno:
   il tetto e' un freno di sicurezza, non una contabilita'.
2. **Budget GCP con soglie** al 50%, 90%, 100% e 120% del tetto mensile: avvisi per email (Monitoring) e ai destinatari dell'account di fatturazione.
   Un budget GCP non blocca la spesa da solo.
3. **Interruttore `ai_enabled=false`**: `scripts/ops_gateway_off.sh off` fa plan -> "SI" -> apply; il gateway risponde 503 a tutto.
   `on` lo riaccende.

## Perche' non budget -> Pub/Sub -> funzione
Avrebbe richiesto una Cloud Function con permessi di modifica sul servizio (un secondo ruolo potente da mantenere), piu' API e codice
da provare, per un risparmio di pochi minuti rispetto al freno gia' presente nel gateway. La scelta piu' semplice e robusta e' tetto
giornaliero automatico + avviso + interruttore manuale sotto controllo di Davide. Se in futuro serve lo spegnimento automatico, si
aggiunge un topic Pub/Sub al budget (`all_updates_rule.pubsub_topic`) e una funzione con ruolo `run.developer` limitato al solo servizio.

## Uso
```bash
scripts/ops_gateway_off.sh off   # mostra il piano, chiede SI, applica
scripts/ops_gateway_off.sh on
```
L'app resta funzionante senza AI (le chiamate AI ricevono 503 dal gateway). L'app ha anche il proprio interruttore e le quote (`/api/admin`).
