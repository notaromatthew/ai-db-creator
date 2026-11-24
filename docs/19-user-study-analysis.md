# Pipeline di analisi RQ0 e RQ3

## Stato

L'analisi dei registri disponibili è completata. Il punto di ingresso
riproducibile è `backend/analyze_available_records.py`; gli output congelati
sono in `backend/reports/user_study_available_records_20261124/`.

L'analisi si basa sui registri compilati disponibili.

## Input

- `Registro_studio_principale_102_casi_STATICO.ods`, foglio `Partecipanti`;
- `Valutazione_cieca_102_casi_STATICA.ods`, foglio `Valutazioni`.

Il collegamento avviene tramite `blind_artifact_id`. Sono inclusi i casi con
screening idoneo, consenso, completamento, verifiche di export/eventi/outcome e
privacy positive, senza ritiro o esclusione approvata.

## Esecuzione

```powershell
cd backend
python analyze_available_records.py `
  --participants ..\outputs\ods_statici_20261124\Registro_studio_principale_102_casi_STATICO.ods `
  --blind-ratings ..\outputs\ods_statici_20261124\Valutazione_cieca_102_casi_STATICA.ods `
  --output reports\user_study_available_records_20261124
```

Il seed è `20261103`; gli intervalli bootstrap usano 5.000 ricampionamenti.

## Disegno analitico

- RQ0: Manuale vs AI + Interfaccia;
- RQ3: AI-only vs AI + Interfaccia;
- outcome primari: qualità dello schema ed errore residuo;
- outcome secondari: tempo di completamento e successo del compito;
- quattro test primari corretti con Holm;
- differenze medie, Cohen's $d$ e intervalli bootstrap al 95%.

## Risultati

Sono inclusi 102 casi validi, 34 per braccio. Il successo è 34/34 in ciascun
braccio. Non emergono differenze negli outcome primari dopo correzione di Holm.
AI + Interfaccia riduce il tempo medio di 13,50 minuti rispetto al Manuale e di
2,12 minuti rispetto ad AI-only.

## Output

- `participant_metrics.csv`;
- `arm_descriptives.csv`;
- `confirmatory_contrasts.csv`;
- `summary.json`;
- `REPORT.md`.
