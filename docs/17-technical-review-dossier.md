# Dossier Tecnico e Priorità

## 1. Scopo

Questo dossier raccoglie una revisione tecnica orientata al rischio, alla robustezza metodologica e alla readiness per un progetto di dottorato. Le osservazioni sono basate sullo stato attuale della repository e sono ordinate per priorità.

## 2. Metodo della revisione

La revisione considera il codice dell'applicazione backend e frontend, la suite di test e la documentazione. I finding sono classificati per priorità (P1 immediata, P2 alta, P3 migliorativa) e per categoria (sicurezza, affidabilità, metodologia, osservabilità).

## 3. Finding e priorità

### Finding P1 — CORS permissivo con wildcard

Riferimento: `backend/app/main.py`.

Problema: la configurazione CORS include `*` insieme ad `allow_credentials=True`. La postura configurativa è troppo permissiva per un sistema che gestisce dati di ricerca, benchmark e cronologie persistenti.

Impatto: alto, sia sul piano sicurezza sia sul piano di maturità verso ambienti più regolati.

Priorità: immediata.

### Finding P1-2 — Autenticazione assente

Problema: nessun meccanismo di autenticazione o autorizzazione per ruolo. Qualsiasi client può creare progetti, eseguire popolamento o accedere ai dati.

Impatto: alto per l'isolamento degli esperimenti e la protezione dei dati in qualsiasi deploy condiviso.

Priorità: immediata (per l'uso condiviso; bassa per laboratorio locale mono-utente).

### Finding P2-1 — Passaggio di sessione request-scoped a task asincroni

Riferimento: `backend/app/tasks.py`, route async (`generate-async`, `populate-async`, `export-async`).

Problema: quando un task asincrono riceve una sessione o risorse legate al ciclo di vita della richiesta, il comportamento può diventare fragile e produrre anomalie intermittenti.

Impatto: medio-alto.

Priorità: alta.

### Finding P2-2 — Migrazioni schema non del tutto formalizzate

Riferimento: `alembic/` e `app/models/database.py`.

Problema: pur essendo presente Alembic, l'evoluzione dello schema non sembra governata come percorso unico tra le versioni.

Impatto: medio.

Priorità: media.

### Finding P3-1 — Osservabilità limitata

Problema: sono presenti log e health endpoint, ma non metriche operative strutturate, tracing o alerting.

Impatto: medio-basso per la ricerca, medio per l'operazione continuativa.

Priorità: media.

## 4. Debito tecnico principale

- autenticazione e ruoli assenti
- CORS permissivo in produzione
- versionamento dei prompt e della configurazione sperimentale non esplicito
- osservabilità limitata a log ed endpoint di health
- migrazioni schema non ancora pienamente formalizzate

## 5. Priorità consigliate per rendere il progetto PhD-ready

1. correggere i finding P1 e rendere sicure le operazioni distruttive
2. introdurre controllo più robusto dei job asincroni
3. formalizzare versionamento di prompt, dataset e campagne sperimentali
4. introdurre audit, auth e hardening minimo
5. migliorare export e analisi dei risultati

## 6. Confronto con l'intervento umano

La revisione tecnica non può determinare, allo stato attuale, alcun impatto comparativo con l'intervento umano. La parte relativa a quanta complessità tecnica residua debba essere assorbita dall'utente nel flusso manuale è da compilare **[non ancora]**: nessun paragone determinato raccolto.