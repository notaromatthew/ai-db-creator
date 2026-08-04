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

## 2026-08-04 - Rate limit LLM e temperatura di campionamento

### Aggiunto

- `AsyncRateLimiter` in `app/core/llm.py` con setting `llm_max_requests_per_minute` (default 15/min, da `.env`): strozzatura a finestra scorrevole applicata a ogni chiamata LLM dell'app (schema, population, adjudication), coordinata tra coroutine concorrenti (FastAPI + benchmark runner). Coperto da `tests/test_rate_limiter.py`.
- Parametro `--temperature` in `run_benchmark.py`, threadato come `temperature` opzionale attraverso `SchemaService.generate_from_prompt` e `PopulationService.populate` fino a `llm.generate_schema` / `llm.generate_sql_for_population`. Default `None` (usa i default pipeline 0.1) per non alterare il comportamento esistente. L'adjudication resta sempre a 0.0 (giudice stabile).

### Impatto sulla comparabilità sperimentale

- A `temperature` bassa (0.1) i run ripetuti di una condizione producono output quasi identici (verificato via hash degli schemi): la media/CI su N run riflette poco la variabilità LLM. Alzando la temperatura (es. 0.5) i run campionano la distribuzione reale; il parametro è registrato per-run e per-condizione nel report per la riproducibilità. Scelta documentata: temperatura alta = misura di distribuzione; bassa = riproducibilità byte-for-byte.

### Validazione eseguita

- Backend: 56/56 test `pytest` verdi (nuovi test rate limiter + firme service aggiornate).
- Smoke test university/full_llm a `--temperature 0.5`: F1 0.31 vs 0.45 su 2 run (varianza reale, prima ~identici a 0.1); adjudication registrata a 0.0.

### Fix

- `llm_adjudication.py`: guardia per risultato `None`/non-dict dal parser LLM (caso osservato in un run del benchmark a temperatura 0.5). Prima un adjudication fallito faceva risalire un `AttributeError` fino al runner marcando l'intero run come errore e perdendo l'F1 deterministico già calcolato. Ora il run resta `ok` con F1, e l'adjudication è registrata con `status:error` e `scores:None`; l'aggregazione filtra i score mancanti. Coperto da `test_adjudicate_returns_error_status_on_none_result`.

## 2026-08-04 - Batch runner benchmark e fix integrità FK

### Aggiunto

- `backend/run_benchmark.py`: esecutore batch che per ogni dataset × condizione × run crea un progetto isolato, carica i sorgenti, genera/popola lo schema e valuta contro la ground-truth. Output: `run<NN>.json` per run, `{condition}.csv` e `{condition}_summary.json` (media + CI di Wilson) per (dataset, condizione).
- Condizioni supportate: `full_llm` (schema generato by LLM) e `baseline` (gold-schema deterministico, popolamento LLM). Ciascun dataset richiede `data/datasets/{name}/prompt.txt` (aggiunti per university, library, hospital).

### Fix

- `backend/app/core/db_generator.py`: i vincoli `FOREIGN KEY` non venivano mai creati nei database generati — `ForeignKey` era passato come kwarg `foreign_key=` (non accettato da SQLAlchemy) invece che posizionalmente. Corretto e coperto da `tests/test_population_pipeline.py::test_foreign_keys_are_built_into_the_generated_database`. Rilevante per RQ2 (le violazioni FK vengono punteggiate a livello di cella).

### Validazione eseguita

- Backend: 40/40 test `pytest` verdi (incluso il nuovo test FK).
- Smoke test del runner sulla condizione `baseline` per il dataset `university` (pipeline end-to-end ok).

## 2026-08-04 - Esecuzione benchmark reale e verifica dinamica LLM

### Eseguito

- Benchmark reale su 3 dataset (university, library, hospital) × 2 condizioni (`full_llm`, `baseline`) × 3 run: 18 progetti isolati, 18/18 completati, report in `backend/reports/benchmark/`.

### Osservazioni sperimentali (separate dalle inferenze)

- `library`: full_llm ≈ baseline (F1 ~0.73); dato tabellare da CSV diretti, ~24 missing sistematici.
- `hospital`: full_llm ha precision più alta (0.84 stabile) e recall più basso; baseline più rumoroso tra i run.
- `university`: full_llm molto più basso (F1 0.23–0.45 vs baseline 0.77). Verificato a mano: il sorgente è denormalizzato e l'LLM deve normalizzare + ricostruire chiavi (ha creato 22/30 studenti con chiavi sintetiche non coincidenti col gold).

### Aggiunto

- `backend/app/evaluation/schema_alignment.py`: allineamento colonne LLM→gold (match normalizzato nomi + fallback `column_alias.json` per-dataset), usato prima della comparazione cella-cella nei run `full_llm`. Registrato nel report per audit.
- `backend/app/evaluation/llm_adjudication.py` + `run_benchmark.py --adjudicate`: verifica dinamica supplementare LLM-as-judge (rubric fissa schema_equivalence/value_accuracy/completeness su 0–100, temperature 0.0, provenance con hash). Eseguita su university/full_llm: F1 0.31 vs giudice 85/90/75 — il giudice discrimina "veramente sbagliato" da "rappresentato diversamente" ed evidenzia l'incompletezza (22/30 studenti).
- `data/datasets/university/column_alias.json`: registry versionato di allineamento (generato `id` → gold `student_id` e `course_id`).

### Validazione eseguita

- Backend: 52/52 test `pytest` verdi (nuovi test per schema_alignment e llm_adjudication).

### Nota metodologica

- Il giudizio LLM è una misura **supplementare, non sostitutiva** del F1 deterministico ed è soggetto a bias di auto-valutazione (stesso modello); riportato con provenance esplicita e non incluso nelle statistiche primarie RQ2.

## 2026-08-03 - Dataset benchmark RQ1/RQ2 (B e C)

### Aggiunto

- `data/datasets/library/` (Dataset B): gold-schema 5 tabelle, ground-truth con 50 libri/20 iscritti/60 prestiti, CSV sorgenti (`members.csv`, `books.csv`, `loans_members.csv`), PDF descrittivo, generatore riproducibile.
- `data/datasets/hospital/` (Dataset C): gold-schema 8 tabelle (patients, doctors, wards, appointments, treatments, medications, prescriptions, invoices), ground-truth con 100 pazienti/200 appuntamenti, CSV sorgenti, note operative TXT, PDF a 3 pagine, generatore riproducibile.
- Entrambi i generatori usano seed fisso (`20260803`) per riproducibilità byte-for-byte.

### Validazione eseguita

- `evaluate_population.py` su ciascun ground-truth contro sé stesso: F1=1.0.
- Simulazione con errori introdotti (valori errati, righe mancanti/extra, violazioni FK): catturati come `wrong_value`, `missing_rows`, `extra_rows`, `fk_violations` con F1 coerente.

### Deviazioni documentate

- Dataset B: prestiti/multe generati a tempo di record; CSV `category_name` denormalizzato.
- Dataset C: 37 colonne vs 42 del protocollo; medici/farmaci impliciti da descrizione/note (vedi README dei dataset).

## 2026-08-03 - Valutazione accuratezza population (RQ2)

### Aggiunto

- Script `backend/evaluate_population.py` per la valutazione cella-cella della population contro un database ground-truth, conforme al protocollo `docs/11-benchmark-protocol.md` (§§4–7, 9).
- Modulo `backend/app/evaluation/population_evaluation.py` con normalizzazione per tipo (numerico, booleano, data), classificazione errori (OK/TC/NS/WV/FK/TM + righe mancanti/extra), allineamento per chiave primaria, verifica FK contro i PK del ground truth e intervalli di confidenza di Wilson.
- Test `backend/tests/test_population_evaluation.py` (5 test: normalizzazione, classificazione, Wilson, confronto perfetto/imperfetto, FK/missing/extra).

### Impatto sperimentale

Rende misurabile RQ2 a livello di cella come definito nel protocollo. La granularità cella-cella richiede una ground-truth con PK allineate al gold schema; i run full-LLM registrano provenance `llm` ma non coordinate sorgente per singola cella (limite già annotato nel run di verifica).

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