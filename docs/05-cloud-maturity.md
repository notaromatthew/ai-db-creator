# Maturità Cloud e Readiness

## 1. Valutazione sintetica

AI-DB-Creator si colloca oggi in una fascia intermedia tra prototipo avanzato e piattaforma di ricerca utilizzabile. L'architettura è abbastanza strutturata da sostenere workflow di ricerca reali, ma non ancora abbastanza governata da essere considerata matura per ambienti enterprise o per la pubblicazione come sistema multi-utente con requisiti forti di sicurezza, identità e audit.

## 2. Maturità per dimensione

### 2.1 Architettura software

**Valutazione: medio-alta**

Il progetto ha una chiara separazione tra frontend, backend, database e servizi esterni (LLM provider), con un'interfaccia REST esplicita e servizi di dominio (schema, document, population, query, metrics, backup) ben incapsulati. Questo riduce il rischio di monoliticità accidentale ed è un segnale positivo di maturità tecnica.

### 2.2 Configurazione e deploy

**Valutazione: medio-bassa**

Esiste un deploy locale ripetibile via `docker-compose.yml`, shadowed dalla guida `docs/04-deployment-guide.md`. Non risultano formalizzate pathway per ambienti multipli (dev/staging/prod), collegamento continuo né versionamento strutturato dei database dell'app licativo.

### 2.3 Dati e persistenza

**Valutazione: media**

Il modello dati è esplicito e persistente (SQLite per lo stato dell'app e per i database generati). Sono presenti backup automatici prima delle operazioni distruttive e procedure di backup/restore manuali (vedi `docs/02-technical-manual.md`). Non risultano però formalizzate policy complete di retention, data lineage e restore con obiettivi RPO/RTO.

### 2.4 Sicurezza

**Valutazione: bassa-media**

Punti di forza:

- configurazione tramite variabili d'ambiente (`backend/config.py`, `.env`)
- rate limiting (`slowapi`)
- log sanitizzato e isolato per progetto (`interaction_logger`)

Aree mancanti:

- autenticazione utenti e autorizzazione per ruoli (assente)
- restrizione CORS in produzione (attualmente wildcard)
- segregazione dati per identità o dominio d'uso
- evidenza di un processo sistematico di hardening applicativo

### 2.5 Osservabilità

**Valutazione: bassa-media**

Sono presenti log strutturati (`loguru`) e un endpoint di health. Non risultano metriche operative strutturate, tracing distribuito o alerting organizzato.

### 2.6 Riproducibilità sperimentale

**Valutazione: media-alta**

La piattaforma salva run, manifesti, hash di input/documenti, provenance di popolazione e log di interazione, quindi la base per la riproducibilità è solida (vedi `docs/15-reproducibility-and-provenance.md`). Serve però disciplina più forte su versionamento di prompt, modelli e snapshot dei dataset.

## 3. Cosa significa in pratica

Il progetto è pronto per:

- lavoro di ricerca rigoroso
- demo accademiche
- test interni
- sviluppo iterativo con più collaboratori

Non è ancora pronto, senza ulteriori interventi, per:

- deployment multi-tenant con responsabilità formalizzate
- uso con dati sensibili su larga scala
- contesti regolati (vedi anche `docs/06-agid-compliance.md`)

## 4. Prossimi salti di maturità consigliati

1. introdurre autenticazione e ruoli
2. formalizzare pipeline di deployment multi-ambiente
3. formalizzare policy di backup, retention e data lineage
4. aggiungere metriche operative, tracing e alerting
5. adottare disciplina formale sulle migrazioni del database

## 5. Confronto con l'intervento umano

L'impatto complessivo della maturità tecnica sull'esito d'uso non può essere ancora valutato in termini comparativi rispetto all'intervento umano. Le cellule relative a questa sezione sono da compilare **[non ancora]**: nessun dato raccolto sulla macchinarica di quanta parte della complessità di deploy/sicurezza sia gestibile senza competenze tecniche, e nessun confronto determinato con l'intervento umano in condizioni manual.