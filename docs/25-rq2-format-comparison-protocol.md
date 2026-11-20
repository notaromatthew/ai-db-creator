# Protocollo RQ2 per il confronto causale fra formati

Stato: protocollo congelato; matrice completata il 20 novembre 2026 e analizzata.

## Obiettivo

Stimare l'effetto del formato di input sul popolamento mantenendo invariati i
fatti osservabili. Questa analisi è separata dalla matrice `combined`, nella
quale documenti eterogenei erano caricati insieme.

## Fixture

Il dataset `data/datasets/format_equivalence/` contiene 45 fatti di iscrizione
universitaria con sette campi. Gli stessi fatti sono codificati in CSV, XLSX,
TXT e PDF. `fixture_manifest.json` congela hash, conteggio e regola semantica.
La validazione automatica confronta CSV e XLSX cella per cella e verifica che
ogni record canonico sia presente integralmente nel testo estratto da TXT e PDF.

## Disegno da congelare prima del primo outcome

- dataset: `format_equivalence`;
- formati: `csv`, `xlsx`, `txt`, `pdf`;
- condizioni: `baseline`, `full_llm`;
- repliche: 5 per cella;
- matrice totale: 4 x 2 x 5 = 40 run;
- ordine: interlacciato per run, formato e condizione;
- temperatura: 0.1;
- concorrenza: 1;
- limite: massimo 10 richieste al minuto;
- retry applicativi: 0;
- `research_mode=true`;
- fallback deterministico: conservato ma contato come fallimento LLM;
- unità di analisi: singolo run.

Provider, modello, limite di output, timeout, revisione Git e calendario devono
essere scritti nel `protocol_manifest.json` della nuova directory prima della
prima chiamata. Non usare un modello diverso fra formati o giorni. Se una quota
impone più giorni, bilanciare ogni giorno fra tutti i formati e le condizioni e
registrare il giorno come variabile di provenienza.

## Comando previsto

Dopo aver congelato provider e modello nell'ambiente:

```powershell
$env:RESEARCH_MODE='true'
$env:LLM_MAX_REQUESTS_PER_MINUTE='8'
$env:LLM_MAX_TOKENS='8192'
$env:GOOGLE_MAX_RETRIES='0'
$env:GOOGLE_TIMEOUT_SECONDS='120'
backend\.venv\Scripts\python.exe backend\run_benchmark.py `
  --datasets format_equivalence `
  --conditions baseline,full_llm `
  --source-formats csv,xlsx,txt,pdf `
  --runs 5 `
  --schedule interleaved `
  --temperature 0.1 `
  --parallel 1 `
  --freeze-protocol `
  --output backend\reports\benchmark_format_equivalence_<provider>_<model>_<date>
```

`--freeze-protocol` crea il manifesto prima di inizializzare il runner e rifiuta
ogni ripresa con revisione, modello o parametri diversi. Il comando deve essere
verificato contro `--help` immediatamente prima dell'esecuzione. Se un'opzione
non esiste, non sostituirla silenziosamente: documentare l'emendamento e
aggiornare il manifest.

## Outcome

Riportare per formato e condizione: tasso di run riusciti senza fallback,
precision, recall e F1 osservabile, discrepanze per categoria, query funzionali
superate ed equivalenza funzionale. I confronti sono descrittivi se la potenza
non è stata definita prima degli outcome. Non combinare questi risultati con la
matrice OpenRouter su sorgenti `combined`.

## Esecuzione osservata

La matrice congelata è stata eseguita con Google Gemini Developer API, modello
`gemini-3.5-flash-lite`, temperatura `0.1`, 8 richieste/minuto, timeout 120
secondi, massimo 8192 token e zero retry applicativi. Il manifest è stato
scritto prima del primo outcome e registra la revisione Git
`0d225aabf6a01ac61d39223df3461e83db1c9170` e la revisione software
`b08c17b85053fd3a`. I 40 run pianificati sono presenti: 38 sono riusciti senza
fallback e due (`csv/full_llm` run 1 e `xlsx/full_llm` run 3) sono terminati con
`LLMException: Schema generation failed`. Non è stato registrato alcun errore
di quota; Nemotron non è stato usato e i due fallimenti non sono stati sostituiti.

Nei run riusciti le metriche non variano tra formati. La baseline ottiene F1
`1.0000` e query funzionali `1.0000` in tutte le celle; `full_llm` ottiene F1
`0.6667` e query funzionali `0.4000`. Il successo tecnico è 5/5 per TXT e PDF,
4/5 per CSV e XLSX nella condizione `full_llm`, e 5/5 in tutte le celle
baseline. Tutti i confronti esatti di Fisher fra formati, corretti con Holm,
sono non significativi. La numerosità ridotta, la singola fixture e la
variabilità metrica nulla impongono un'interpretazione esplorativa: i dati non
dimostrano equivalenza generale fra formati.

Artefatti e analisi riproducibile:

- `backend/reports/benchmark_format_equivalence_google_gemini35flashlite_20261120/`;
- `backend/analyze_rq2_format_matrix.py`;
- `backend/reports/rq2_format_analysis/`.

## Recovery selettivo post-outcome

I due fallimenti sono stati successivamente ripetuti una sola volta con la
stessa configurazione Gemini, in un output separato. Entrambi sono riusciti con
popolamento LLM e senza fallback, ottenendo F1 `0.6667` e query funzionali
`0.4000`. La sensibilità dimostra recuperabilità tecnica, non identifica la
causa degli errori iniziali e non modifica il risultato primario di 38/40.
Manifesto, hash e limiti sono in
`backend/reports/benchmark_format_equivalence_google_gemini35flashlite_selective_recovery_20261120/`.
