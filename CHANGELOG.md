# Changelog

Tutte le modifiche rilevanti del progetto sono raccolte in questo file. Il formato segue una struttura orientata alla ricerca: ogni voce distingue funzionalità applicative, infrastruttura scientifica, riproducibilità, documentazione e validazione.

## 2026-08-03 - Rilascio baseline per GitHub (app v1.0.0)

### Sintesi

Questa iterazione consolida AI-DB-Creator come piattaforma di ricerca per la generazione di database relazionali assistita da LLM. Il lavoro trasforma il progetto da prototipo applicativo a base sperimentale robusta per attività di dottorato: pipeline di popolamento deterministic-first, riproducibilità fondata su manifesti e hash, log di interazione sanitizzati e documentazione allineata agli standard di un progetto di ricerca PhD.

### Pipeline di popolamento

- Popolamento deterministic-first per documenti strutturati CSV/XLSX: le regole di mappatura esatte o parziali vengono eseguite per prime; per le colonne non risolte si attiva la mappatura semantica via LLM.
- Fallback LLM per documenti non strutturati (PDF/TXT).
- Provenance tracciabile per riga: metodo di mappatura, coordinate di origine, esito (inserted/duplicate/failed) e chiave di riga.
- Le righe fallite mantengono una traccia separata non materializzata, con `reason` (es. `constraint_or_type_error`).
- Troncamento dell'input LLM a 5000 caratteri per documento, con warning esplicito.
- Rifiuto degli INSERT multi-riga generati via LLM senza esecuzione.

### Persistenza e schema

- Modelli `Project` e `Document` persistiti in SQLite, con relazioni di ownership.
- Migrazioni gestite via Alembic (migrazione iniziale `c25c5721cbb9`).
- Export multi-dialetto (SQLite, PostgreSQL, MySQL, SQL Server).

### Frontend

- Workflow guidato con step che si completano quando i dati sono disponibili.
- CRUD visuale sui dati: modifica celle inline, aggiunta ed eliminazione di righe, filtri per colonna e per tabella.
- Editing dello schema con aggiunta e rimozione di colonne e tabelle.
- Import SQL multipart che gestisce punto e virgola all'interno delle stringhe, dialetto e limite di dimensione.

### Ricerca e riproducibilità

- Manifest degli esperimenti con hashes di input, schema iniziale e finale e artefatti di run.
- Cronologia sanitizzata: nessun dato personale negli eventi.
- Rimozione per-progetto coerente con gli artefatti di proprietà.

### Fix e robustezza (Python 3.13)

- Corretto `os.unlink` (WinError 32) su Windows per i file temporanei di upload: retry con backoff invece di un singolo tentativo.
- Passaggio da `INSERT OR IGNORE` a `INSERT` per non mascherare le violazioni di vincolo nel conteggio delle righe fallite.

### Ambiente e configurazione

- Aggiunto `backend/.python-version` (3.13).
- Documentato l'uso di un ambiente virtuale isolato con Python 3.13.
- Rotazione della chiave API nel file `.env` (svuotata) — vedere `AGENTS.md` per il processo.

### Validazione eseguita

- Backend: 33/33 test `pytest` verdi con l'ambiente virtuale Python 3.13.
- Frontend: `npm run test` (7 test) e `npm run build` (tsc + vite) verdi.
- Security audit eseguito e documentato in `frontend/NPM_AUDIT_REPORT.md`.

### Note metodologiche

- Le metriche automatiche sono euristiche riproducibili pensate per ricerca e confronto sperimentale, non per validazione autonoma.
- Le parti che prevedono il confronto con l'intervento umano restano intenzionalmente incomplete (segnaposto).

## 2026-08-03 - Popolamento full-LLM come percorso primario

### Cambiamento

La pipeline di popolamento è stata invertita: il percorso full-LLM è ora quello primario per ogni tipo di documento (CSV, Excel, PDF, TXT), non più un fallback. L'LLM riceve il contenuto completo dei documenti e decide come mappare i valori nello schema, scartando solo le righe già presenti nelle tabelle target (duplicati) e accettando valori NULL/vuoti dove lo schema li consente. Il mapper deterministico resta solo come percorso di recupero quando l'LLM non restituisce SQL utilizzabile.

### Motivazione (osservazione sperimentale)

In un run di prova su file denormalizzati multiprogetto, 29/30 inserimenti fallivano (`constraint_or_type_error` su NOT NULL/FK): il mapper deterministico a sottostringhe associava `id` (sottostringa di `ID_Scontrino`/`Codice_Prodotto`) a più tabelle senza valorizzare colonne NOT NULL e FK, lasciando il database quasi vuoto.

### Dettagli implementativi

- Rimossa la condizione `has_structured_data`: il gate dell'LLM ora è attivo quando il testo dei documenti non è vuoto.
- Rimossi i limiti artificiali sulle righe tabellari inviate all'LLM (era 150 righe per tabella); il contenuto completo delle tabelle viene incluso.
- Provenance: l'estrazione registra ora `llm` come metodo predefinito; `deterministic`/`hybrid` restano solo nel percorso di fallback.
- Test aggiornati: `test_deterministic_fallback_runs_when_llm_sql_is_empty_and_has_traceable_provenance`, `test_full_llm_is_called_for_structured_csv`; test hybrid/multi-source/failed aggiornati a mock LLM vuoto.

### Impatto sulla comparabilità sperimentale

Il cambiamento modifica la semantica di popolamento rispetto alle iterazioni precedenti: l'estrazione path predefinita passa da `deterministic` a `llm`. Documentato esplicitamente in `docs/00`, `docs/01`, `docs/02`, `docs/03`, `docs/07`, `docs/15`.

### Validazione eseguita

- Backend: 34/34 test `pytest` verdi (incluso il nuovo test full-LLM).