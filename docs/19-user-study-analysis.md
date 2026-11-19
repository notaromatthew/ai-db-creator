# Pipeline di analisi RQ0, RQ3 e RQ4

## Stato

`backend/analyze_user_study.py` è il punto di ingresso riproducibile predisposto per gli export pseudonimi dello studio. Non contiene dati simulati e non genera risultati finché non riceve una matrice completa di casi osservati. Per impostazione predefinita interrompe l'analisi se manca l'outcome finale di un partecipante completato.

Il target confermativo è almeno 34 casi completati per ciascuno dei tre bracci. Un campione inferiore non viene automaticamente reinterpretato: deve essere dichiarato esplorativo nel paper.

## Input

### `participants.csv`

È l'export `kind=participants` del pannello ricercatore. Le colonne usate sono:

- `participant_id`
- `arm`: `manual`, `ai_only` oppure `ai_interface`
- `completed`
- `withdrawn`
Il protocollo corrente non raccoglie colonne NASA-TLX o SUS. La loro assenza è prevista dall'emendamento e non rappresenta missing data.

### `events.csv`

È l'export combinato `kind=interactions`, che include sia gli eventi del
percorso partecipante sia la telemetria pseudonima dell'app. Deve contenere:

- `participant_id`
- `arm`
- `type`
- `created_at`: timestamp ISO 8601
- `data`: JSON pseudonimo

Ogni caso incluso deve avere esattamente un evento `task_start` e un evento `task_end` successivo.

### `outcomes.csv`

È prodotto dopo la valutazione cieca dell'output finale di ogni partecipante. Deve contenere:

- `participant_id`
- `dataset`
- `schema_quality`: media o punteggio congelato 1–5
- `residual_error_rate`: proporzione 0–1 calcolata con lo stesso valutatore automatico in tutti i bracci
- `task_success`: booleano

La procedura che crea questo file deve essere congelata prima di osservare i confronti tra bracci. Il file non deve contenere nomi, email, account, indirizzi IP o testo grezzo delle chat.

## Esecuzione

```powershell
cd backend
.\.venv\Scripts\python.exe analyze_user_study.py `
  --participants exports\participants.csv `
  --events exports\interactions.csv `
  --outcomes exports\outcomes.csv `
  --output reports\user_study_analysis
```

Il seed predefinito è `20261103` e il bootstrap usa 5.000 ricampionamenti.

## Output

- `participant_metrics.csv`: matrice analitica pseudonima e tempi derivati
- `arm_descriptives.csv`: descrittive per braccio
- `confirmatory_contrasts.csv`: RQ0 Manuale vs AI + Interfaccia e RQ3 AI-Only vs AI + Interfaccia
- `rq4_patterns.csv`: pattern sequenziali con supporto minimo 0,30
- `rq4_correlations.csv`: correlazioni di Spearman con correzione Benjamini–Hochberg
- `rq4_clusters.csv`: clustering esplorativo `k=3..5` quando numerosità e variabilità lo consentono
- `manifest.json`: hash degli input, seed, numerosità e famiglia di test
- `REPORT.md`: nota metodologica generata

## Molteplicità e interpretazione

La famiglia confermativa comprende quattro test: due contrasti preregistrati per due outcome primari (`schema_quality` e `residual_error_rate`). I p-value Welch sono corretti con Holm. Il tempo è secondario. Pattern, correlazioni e cluster RQ4 sono esplorativi e non vanno presentati come confermativi. NASA-TLX e SUS sono esclusi dallo studio corrente in base all'emendamento del 18 novembre 2026.

La pipeline non decide esclusioni, eleggibilità, deviazioni dal protocollo o interpretazioni causali: tali decisioni devono essere documentate e approvate prima di sbloccare l'analisi finale.
