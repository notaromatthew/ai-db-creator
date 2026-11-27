# Changelog

## 2026-11-27 - Correzioni di sicurezza (revisione del repository)

- Chiave amministratore della valutazione esperti: rimosso il valore predefinito `admin123`. `ADMIN_SECRET_KEY` deve essere impostata; se è vuota il pannello amministratore resta disattivato. Confronto a tempo costante, chiave accettata solo nell'intestazione `X-Admin-Key` (non più nell'URL), blocco temporaneo dopo 10 tentativi falliti in 15 minuti per indirizzo (HTTP 429). L'esportazione CSV del frontend scarica ora con l'intestazione.
- Endpoint `/api/expert/*` (elenco e dettaglio schemi, valutazioni proprie, invio): ora richiedono il login. Con l'autenticazione attiva l'identità del valutatore è `preferred_username` del token; il campo `evaluator_name` inviato dal client è ignorato. Con l'autenticazione disattivata (sviluppo e test) resta il nome inviato. Chi valuta deve quindi avere un account; le valutazioni già raccolte non vengono modificate.
- Dipendenze: `python-multipart` 0.0.12 -> 0.0.32; sostituito `python-jose` 3.3.0 con PyJWT 2.15.0 per la verifica dei token (resta `RS256` obbligatorio, con tolleranza di 30 secondi sull'orologio).
- Nessuna modifica a prompt, metriche o popolazione degli esperimenti.

## 2026-11-24 - Chiusura analisi RQ0/RQ3 e rimozione RQ4

- Rimossa RQ4 dal perimetro empirico corrente, mantenendo il logging come funzionalità tecnica della piattaforma.
- Analizzati 102 casi validi dai registri disponibili, con 34 casi per ciascun braccio.
- Congelati descrittive, contrasti Welch, correzione di Holm, effect size e intervalli bootstrap in `backend/reports/user_study_available_records_20261124/`.
- Osservata qualità finale equivalente fra i bracci e una riduzione del tempo medio per AI + Interfaccia rispetto a Manuale e AI-only.
- Sostituiti nel paper i segnaposto RQ0/RQ3 con risultati, discussione e conclusione; riallineata la documentazione metodologica.

## 2026-11-18 - Emendamento pre-raccolta RQ0/RQ3/RQ4

- Registrata come determinazione istituzionale riferita dall'utente la comunicazione che l'approvazione etica preventiva non è richiesta per lo studio corrente; consenso, ritiro e minimizzazione dei dati restano invariati.
- Esclusi Raw NASA-TLX e SUS dal protocollo corrente e riservati a un'eventuale revisione futura separata.
- Semplificato il percorso partecipante a compito, debrief e completamento; gli endpoint questionario rifiutano nuove risposte nel flusso corrente.
- Allineati export e pipeline di analisi: gli outcome primari restano qualità dello schema e tasso di errori residui, mentre il tempo resta secondario.

## 2026-11-18 - Completamento del pannello RQ1 a tre esperti

- Integrato il terzo export di 30 valutazioni, ottenendo il pannello pianificato di 3 esperti × 30 schemi senza pooling con i 45 trained student raters.
- Estesa l'analisi a sorgenti CSV multiple con formati misti, mantenendo hash separati, input canonico pseudonimizzato e assenza di identificativi originali negli artefatti.
- Aggiornati accordo e confronto fra condizioni: alpha complessivo 0,054, accordo esatto 20/150 celle e D1 full-LLM meno baseline +0,800 (p Holm 0,0021). Il basso accordo impedisce di presentare il pannello come consenso forte.
- Registrata come ancora mancante la conferma esplicita di indipendenza e cecità alle condizioni del terzo esperto; l'idoneità deriva dalla qualifica fornita dall'utente.
- Rimossi dagli artefatti pubblicabili RQ1 i timestamp delle valutazioni e qualsiasi durata derivata; i file sorgente grezzi restano invariati e sono rappresentati solo tramite hash.

## 2026-11-14 - Replica RQ1 separata con due esperti

- Integrato un export headerless semicolon di 60 valutazioni come replica separata, senza pooling con i 45 trained student raters e senza persistere gli identificativi originali.
- Aggiunto `backend/analyze_rq1_expert_replication.py` con validazione 2×30, input canonico pseudonimizzato, hash distinti sorgente/canonico, descrittive, accordo ordinale e confronto a livello schema.
- Documentata la deviazione 2 esperti osservati vs 3 pianificati, l'attestazione utente di indipendenza e cecità, l'accordo perfetto osservato senza inferenze causali e D2 costante con statistiche inferenziali non definite.

Tutte le modifiche rilevanti del progetto sono raccolte in questo file. Il formato segue una struttura orientata alla ricerca: ogni voce distingue funzionalità applicative, infrastruttura scientifica, riproducibilità, documentazione e validazione.

## 2026-11-13 - Recupero della matrice collegata alle valutazioni RQ1

- Recuperata la matrice storica completa 3×2×5 che ha generato i 30 schemi valutati; verificati mapping seed 42 e corrispondenza strutturale diretta 30/30 fra codice anonimo e `schema_json` del progetto.
- Creato `recover_expert_linked_matrix.py` con guardie sull'output, marker di completamento, manifesti SHA-256 e snapshot sanitizzato; il vecchio `app.db` completo non viene redistribuito perché contiene dati estranei.
- Verificati 30/30 database integri e non vuoti, 100/100 record documento collegati a upload esistenti e 100/100 hash coincidenti con le sorgenti storiche.
- La matrice è classificata `primary_expert_linked` per RQ1 e `recovered_historical_secondary` per RQ2. Le matrici RQ2 strutturate restano separate e non vengono sostituite.
- Rivalutati offline i 30 database con il valutatore corrente; risultati e limiti sono documentati in `docs/22-rq1-expert-linked-matrix-recovery.md`.

## 2026-11-07 - Secondo tentativo dei tre errori OpenRouter

- Ritentati in modalità `--resume --retry-failed` soltanto Hospital `full_llm` run 2, 3 e 4 del recovery selettivo, mantenendo invariati modello e parametri.
- I tre run hanno nuovamente fallito durante la generazione dello schema; gli otto run già riusciti non sono stati rieseguiti né sovrascritti.
- Aggiunto `retry_attempt_20261107.json` per registrare selezione, configurazione e outcome; i tre errori non sono interpretati come punteggi prestazionali pari a zero.
- Dopo il reset della quota, una richiesta minima ha verificato la disponibilità del provider e i tre run sono stati ripetuti singolarmente: il run 3 è riuscito, i run 2 e 4 hanno restituito uno schema non analizzabile. La cella Hospital `full_llm` passa così a 3/5 successi; il nuovo tentativo è registrato in `retry_after_quota_reset_20261107.json`.
- Introdotto come opt-in `schema-json-v2`, che invia a OpenRouter il JSON Schema di `NormalizedSchema` e mantiene invariato il contratto legacy per default. Nella sensibilità selettiva preregistrata, i due errori residui Hospital `full_llm` (run 2 e 4) sono riusciti entrambi; F1 medio `0.4802`, query funzionali `0.0000`. I risultati restano separati dai run legacy.
- Preregistrata una nuova matrice completa `schema-json-v2` su due giorni, con 15 run bilanciati per dataset in ciascun giorno e 16384 token massimi. Il blocco del 7 novembre è completo: 15/15 successi, 97 hash artefatto e 50 hash sorgente verificati senza discrepanze; gli aggregati restano intermedi fino al blocco dell'8 novembre.

## 2026-11-08 - Completamento matrice OpenRouter strutturata

- Completato il secondo blocco preregistrato: 15/15 successi. La matrice finale raggiunge 30/30 run riusciti, zero fallback, una revisione software e configurazione uniforme `schema-json-v2`.
- Verificati 195 hash artefatto, 100 hash sorgente e 30 hash delle specifiche di valutazione senza discrepanze; scansione segreti pulita.
- Risultati finali F1/query funzionali: University baseline `0.9638/0.4400`, University `full_llm` `0.6651/0.3600`, Library baseline `0.9348/0.6200`, Library `full_llm` `0.9848/0.4000`, Hospital baseline `0.9496/0.4200`, Hospital `full_llm` `0.6427/0.2000`.
- Il giorno 2 mostra F1 inferiore in quattro celle su sei; la possibile deriva temporale del provider resta una limitazione descrittiva. La matrice non viene aggregata con Gemini, pilot legacy o recovery selettivi.

## 2026-11-06 - Pilot OpenRouter con modelli gratuiti

- Il client OpenRouter invia esplicitamente `reasoning.enabled=false`, limita i token di output e applica timeout e retry configurabili. Il cambiamento evita che i modelli reasoning gratuiti consumino l'intero budget senza restituire il JSON dello schema.
- Le esecuzioni OpenRouter restano pilot separati e non vengono aggregate con la matrice Gemini RQ2.
- Il pilot University `full_llm` con `nvidia/nemotron-3.5-super-vl:free` è terminato senza fallback: precisione 0,8333, recall 0,6737, F1 0,6899 e query funzionali 0,3000. Il risultato singolo è solo una verifica di fattibilità.
- Il runner accetta `--run-indices` per eseguire un insieme esplicito di repliche, evitando di rieseguire celle già riuscite durante i recovery selettivi.
- Il recovery OpenRouter degli 11 errori Gemini ha prodotto 8 run riusciti e 3 errori di parsing dello schema Hospital `full_llm`; 11 manifest e 57 hash sono stati verificati. I risultati restano una sensibilità selettiva e non vengono combinati con Gemini.
- Preregistrata prima dell'esecuzione una matrice Nemotron completa 3×2×5 in una directory nuova, con ordine interlacciato e limite output 8192; resta una sensibilità OpenRouter separata dalla matrice Gemini e dal recovery selettivo.

## 2026-11-05 - Esecuzione primaria RQ2 e controllo del fallback

- Il runner assegna i progetti batch all'account tecnico `research-benchmark-runner`, coerentemente con il vincolo `owner_id` obbligatorio.
- I run che ricadono sul popolamento deterministico sono ora marcati come falliti (`population_mode=fallback`) e non entrano negli aggregati RQ2.
- Prima di osservare outcome primari, il protocollo è stato emendato da `gemini-2.5-flash-lite`, non più disponibile per nuovi utenti, a `gemini-3.5-flash-lite`, verificato con una richiesta minima riuscita sulla Gemini Developer API.
- Corretto il supporto alle risposte Gemini in content blocks, che causava falsi fallback tramite `.strip()` su liste; aggiunta ripresa sicura dei bundle con verifica di provider, modello e temperatura.
- La matrice v2 contiene 30/30 manifest con zero errori di hash, ma resta descrittiva: la quota del provider si è esaurita nei run Hospital `full_llm` eseguiti per ultimi, confondendo condizione e ordine temporale.
- Il controllo QA ha inoltre classificato la v2 come pilot: usa due revisioni software, `research_mode=false`, omette gli hash sorgente nei nove fallimenti precoci e contiene un `ci95_f1` Wilson non valido per la media degli F1 per-run; questi limiti sono dichiarati senza riscrivere gli artefatti congelati.
- Il runner successivo registra gli hash dei sorgenti anche quando la generazione schema fallisce, separa run valutabili, non valutabili ed errori, termina con exit nonzero sugli errori e sostituisce il Wilson improprio sulla media F1 con il solo range descrittivo osservato. Gli artefatti v2 congelati non vengono riscritti.
- La selezione del provider LLM è ora fail-closed: provider sconosciuti e dipendenza Google assente producono un errore esplicito invece di un fallback OpenAI con provenance incoerente; il rate limiter recepisce gli aggiornamenti runtime.
- Aggiunta l'opzione esplicita `--resume --retry-failed`: dopo aver verificato manifest e configurazione conserva i run `ok` e `not_evaluable` e riesegue esclusivamente quelli con `status=error`, senza riscrivere gli altri artefatti.
- Aggiunto il contratto di output schema opt-in `schema-json-v2`: con `OPENROUTER_SCHEMA_JSON_MODE=true`, OpenRouter riceve il JSON Schema completo di `NormalizedSchema` esclusivamente durante la generazione schema; il default resta `legacy-pydantic-v1` per riprodurre gli esperimenti precedenti. Se il parser primario fallisce viene tentata una sola estrazione JSON deterministica locale con validazione Pydantic. Prompt e semantica restano invariati; manifest e retry verificano la versione del contratto e la diagnostica registra solo categoria, finish reason e token, senza prompt, documenti o output grezzi.

## 2026-11-04 - Protocollo osservabile ed equivalenza funzionale RQ2

- Aggiunte specifiche versionate `evaluation_spec.json` per University, Library e Hospital con scope osservabile, chiavi naturali, canonicalizzazione, soglie congelate e dieci query funzionali per dataset.
- Corretto il valutatore cell-level: valori numerici/date/booleani differenti non sono più classificati come equivalenti; `NULL` resta distinto dalla stringa vuota; lo scope osservabile è applicato simmetricamente e le righe relazionali possono essere allineate tramite chiavi di business invece degli ID sintetici.
- Il runner supporta celle isolate per formato, mantiene separata la sensibilità full-gold e genera per ogni run un bundle autosufficiente con database, schema, valutazione, ledger, allineamento, risultati delle query, manifest e hash.
- L'equivalenza funzionale verifica query critiche, result hash e differenze, duplicati di chiavi naturali e violazioni FK. Errori e metadata sensibili vengono redatti prima della persistenza.
- Documentata l'assenza di varianti XLSX e la non equivalenza fattuale degli attuali file CSV/PDF/TXT: nessuna conclusione causale sul formato viene prodotta finché non sarà validato un unico fact set reso nei quattro formati.
- RQ1 descrive il campione osservato come `trained student raters`, non come esperti professionali; la deviazione dal protocollo pianificato resta esplicita.
- Validazione: 26 test RQ2, 16 test delle pipeline di ricerca, 110 test frontend, build Vite e compilazione LaTeX completati.

## 2026-11-03 - Chiusura automatizzabile RQ1 (Branch redesign/tecnia-research)

- Aggiunto `backend/analyze_rq1_ratings.py`: valida la matrice completa, pseudonimizza i valutatori, calcola descrittive, effetto soffitto, alpha di Krippendorff ordinale con bootstrap, confronto fra condizioni a livello di schema, correzione Holm e sensibilità appaiata dataset/run.
- Generato `backend/reports/rq1_analysis/` da 1.350 valutazioni (45 valutatori × 30 schemi), senza marcare singole risposte come nuove o imputate. Il manifesto registra hash, revisione, seed e parametri.
- Corretto il contratto della scala RQ1 da 0–4 a 1–5 nel generatore e nel pacchetto esperti; ricreato `ratings_template.csv`.
- Rimosso il lock temporaneo OpenOffice dal pacchetto e aggiunta la relativa regola a `.gitignore`.
- Documentata la deviazione tra i tre esperti pianificati e i 45 valutatori osservati, che richiede verifica umana dei criteri di idoneità prima dell'interpretazione confermativa.

## 2026-11-03 - Preparazione analisi RQ0/RQ3/RQ4 e allineamento del protocollo

- Allineato il target operativo del pannello dello studio al protocollo confermativo: 34 completamenti per braccio invece di 20.
- Aggiunto `backend/analyze_user_study.py`, che valida gli export pseudonimi, deriva i tempi dagli eventi, esegue i contrasti preregistrati RQ0/RQ3 con correzione Holm e prepara pattern, correlazioni FDR e cluster esplorativi RQ4.
- Aggiunti test della matrice completa, delle correzioni per confronti multipli e degli artefatti generati.
- Documentato il contratto degli input in `docs/19-user-study-analysis.md`; la pipeline non produce risultati senza outcome osservati completi.
- Corretto lo stato scientifico di RQ2: il codice di valutazione è presente, ma gli artefatti grezzi e aggregati citati nella bozza non sono nella copia corrente e devono essere recuperati o rigenerati prima della pubblicazione.
- Aggiornati roadmap e paper per distinguere le condizioni benchmark RQ1 (`baseline`, `full_llm`) dai bracci partecipanti RQ0/RQ3 e per rimuovere attività tecniche già completate dalla checklist.
- Propagato il contesto pseudonimo fra pagina dello studio e applicazione; il backend verifica account, partecipante e braccio, impedisce modifiche/chat ad AI-Only e chiamate AI al braccio Manuale, esporta eventi granulari RQ4 e cancella la telemetria collegata al ritiro.
- Aggiornati Vite 5→8, Vitest 2→5, React Router 6→7 e il plugin React compatibile; l'audit npm passa da 15 vulnerabilità a 0. Le route secondarie e il diagramma sono caricati in modo differito, eliminando i warning Vite sul chunk principale e riducendolo da circa 682 kB a 386 kB.

## 2026-10-14 - Pagina Esempi pubblica, impostazioni solo Vertex AI (Branch redesign/tecnia-research)

- Nuove API pubbliche in sola lettura: `GET /api/examples`, `/api/examples/{name}`, `/api/examples/{name}/files/{filename}`. Leggono `data/datasets/{library,university,hospital}` (nome da elenco fisso, file solo se elencati in `source/`); il `Dockerfile` copia i dataset in `/app/example_datasets`. Nessuna chiamata AI, nessuna scrittura.
- Frontend: pagine `/app/examples` e `/app/examples/:name` senza login, voce "Esempi" nel menu e nella landing. I testi di spiegazione stanno in `data/datasets/examples.json` (scritti a mano, non generati).
- Impostazioni: `/app/settings` mostra solo Vertex AI (modello tra `gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`, lunghezza massima, prova di connessione). `PUT /api/settings` rifiuta modelli fuori elenco; rimossi gli endpoint Ollama di settings e i controlli temperatura/top-p/richieste al minuto, che non avevano effetto su Vertex.
- Produzione a costo minimo: `docker-compose.coolify.yml` chiama Vertex direttamente (`VERTEX_CREDENTIALS_JSON`), senza gateway; `VERTEX_ALLOWED_MODELS` limita i modelli scelti dalle impostazioni; tetti piu' bassi (`DAILY_AI_BUDGET_TOTAL` 150, quota utente 10). Piano Terraform per service account `aidb-prod` e budget in `infra/gcp/local-dev/prod.tf` (non applicato). Vedi `docs/ops/vertex-diretto.md`.
- Ollama rimosso dal prodotto: eliminati provider, impostazioni (`use_ollama`, `ollama_*`), dipendenza `langchain-ollama` e voci Ollama nella pagina Benchmark; il default di `LLM_PROVIDER` e' `vertex`. Il badge del modello mostra solo Vertex AI. Correzione: `use_ollama` valeva `true` di default e in produzione ogni generazione finiva su un server Ollama non raggiungibile (la generazione restava ferma su "Tabelle individuate"). `token_cost` e confronti con run precedenti che usavano Ollama non sono piu' riproducibili.
- Correzione: con `VERTEX_MAX_OUTPUT_TOKENS=2048` gli schemi medio-grandi (es. ospedale, 10 tabelle) venivano troncati dal modello (`finish_reason=MAX_TOKENS`) e la generazione falliva con "Schema generation failed". Il default sale a 8192 (config e compose di produzione) e il log registra `finish_reason` e token di uscita quando l'output non e' valido. Non cambia prompt ne' modello.
- Chat dello schema: l'assistente ora fa una proposta breve (max 90 parole, mai JSON o SQL nel testo) e lo schema cambia solo dopo la conferma, con il pulsante "Applica le modifiche" o scrivendo "sì". Il JSON dello schema resta sul server: dopo la conferma si genera lo schema completo aggiornato, che si salva come prima (`PUT /schema`). Nuovi `POST /api/projects/{id}/chat/apply` e `.../chat/dismiss`; `POST /chat` restituisce `{response, proposal, schema}`. Migrazione `h8chatprop00008` (`chat_messages.proposal`). Le risposte sono rese in Markdown (grassetto, elenchi, codice), senza HTML. Versione prompt `schema_chat_prompt_v2`, non comparabile con la v1 (vedi `docs/15-ai-agent-changelog.md`).
- Infrastruttura: `infra/gcp/local-dev` (progetto GCP di sviluppo con Vertex AI, importato in Terraform), `docker-compose.local.vertex.yml`, admin locale predefinito.

## 2026-10-12 - Lifespan, /ready, test, correzioni e deploy GCP (Branch Davide)

- Backend: migrazione a `lifespan` (RFC-001), endpoint `/ready`, `PORT`/CORS da configurazione; avvio resiliente se DB o Keycloak non rispondono. 26 nuovi test (auth, health/ready, settings, benchmark, multi-tenancy): 91 passati.
- Correzione: `POST /api/benchmark/run` restituiva sempre 500 (stima token); `token_cost_estimate` ora è definito da questa data e non comparabile con run precedenti (nessuno salvato).
- Correzione: `GET/DELETE /api/projects/{id}` ora verificano la proprietà (RFC-005).
- Frontend: 21 nuovi test (28 totali). Corretto `SettingsPage`: temperatura 0 veniva salvata come 0.1; impatta la riproducibilità solo per chi imposta 0.
- Deploy: `Dockerfile` con `$PORT` e utente non-root, `deploy/gcp/` (Cloud Build, Cloud Run, Secret Manager), capitolo GCP in `docs/04-deployment-guide.md`.
- Aperti: vedi RFC-007.

## 2026-08-07 - Feature Fondamentali, Keycloak, PostgreSQL, SonarQube, Benchmark & Coolify (Branch Davide)

### Sintesi

Questa iterazione sul branch `Davide` introduce le funzionalità fondamentali per la segregazione multi-tenant, il salvataggio persistente su database PostgreSQL online, l'integrazione con Keycloak per la gestione utenti, il controllo qualità del codice con SonarQube, e una pagina dedicata ai Benchmark scientifici con supporto al voto degli utenti/esperti e all'esportazione di tabelle LaTeX per il Paper.

### Autenticazione & Multi-Tenancy (Keycloak)

- Integrazione OIDC con server Keycloak (`89.168.29.98:8080`) e provisioning automatico del Realm `aidbcreator` e Client `aidbcreator-app` via API Admin (`backend/app/core/keycloak_setup.py`).
- Middleware FastAPI JWT Bearer in `backend/app/core/auth.py` per l'estrazione dell'utente autenticato e isolamento dei progetti via `user_id`.
- `KeycloakContext.tsx` per il frontend React con supporto al SSO, token refresh e fallback dev-mode trasparente.

### Persistenza (PostgreSQL Online)

- Transizione della base dati di sistema verso PostgreSQL online (`89.168.29.98:12000`).
- Fallback automatico in-memory / SQLite locale in caso di disconnessione di rete.

### Qualità del Codice (SonarQube)

- File di configurazione `sonar-project.properties` e script `scripts/run_sonar_scan.sh` per la scansione statica sia del backend Python che del frontend TypeScript.

### UX & Aiuto

- Modal `ProjectWizardModal.tsx` con scelta guidata tra **Flusso Rapido (Manuale)** e **Wizard Guidato (Step-by-Step)**.
- Nuova sezione `/help` (`HelpPage.tsx`) con guida passo-passo interattiva.

### Configurazione AI & Benchmark Scientifico

- Nuova pagina `/settings` per variare dinamicamente Provider AI (Google Gemini, OpenAI, Groq, OpenRouter, Ollama) e iperparametri (temperatura, top_p, max_tokens, rate limit).
- Nuova pagina `/benchmark` (`BenchmarkPage.tsx`) con 3 scenari Gold Standard predefiniti, metriche automatiche (3NF %, Rel F1, Cell Precision, Latency), form per la **valutazione soggettiva dell'esperto (Likert 1-5)** e pulsante di esportazione della tabella in sintassi **LaTeX** per il Paper.

### Deploy su Coolify

- `Dockerfile` multi-stage per la compilazione assets e il servizio unificato.
- `docker-compose.coolify.yml` pronto per il deployment automatizzato su Coolify.

---



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
