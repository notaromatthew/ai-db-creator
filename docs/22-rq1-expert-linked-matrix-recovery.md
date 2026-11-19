# Recupero della matrice collegata alle valutazioni RQ1 — 13 novembre 2026

## Classificazione

La matrice storica recuperata è l'artefatto primario per RQ1 perché è la
matrice da cui sono stati prodotti i 30 schemi anonimi valutati. Non sostituisce
la matrice RQ2 strutturata del 7–8 novembre: per RQ2 è una rivalutazione storica
secondaria, calcolata a posteriori con il valutatore corrente.

| Uso | Classificazione |
|---|---|
| RQ1, collegamento valutazioni-schema-condizione | `primary_expert_linked` |
| RQ2, accuratezza ed equivalenza funzionale | `recovered_historical_secondary` |
| Matrici RQ2 più recenti | conservate e non sostituite |

## Evidenze osservate

- La matrice contiene 30 run distinti: 3 dataset, 2 condizioni e 5 repliche.
- Tutti i 30 `project_id` sono presenti nel database applicativo storico.
- Tutti i 30 database generati sono presenti, non vuoti, superano
  `PRAGMA integrity_check` e non mostrano violazioni in
  `PRAGMA foreign_key_check`.
- Il pacchetto storico e quello corrente hanno la stessa mappatura anonima.
- La mappatura è riproducibile con il seed 42.
- Tutti i 30 file `S*.md` coincidono strutturalmente con lo `schema_json` del
  progetto indicato dalla mappatura: tabelle, colonne, vincoli e relazioni.
  Le differenze testuali del pacchetto corrente sono soltanto traduzioni delle
  frasi introduttive.
- I 30 progetti hanno 100 record documento. Tutti i 100 upload referenziati
  esistono e coincidono tramite SHA-256 con le sorgenti storiche del rispettivo
  dataset. Gli hash sono stati calcolati durante il recupero, non erano stati
  congelati prima delle chiamate LLM.
- `university/full_llm/run04` ha `status=error` nel record storico per un errore
  successivo di adjudication/metrica; schema e database sono presenti e
  valutabili.

## Provenienza non recuperabile come fatto originale

I record storici non contengono manifesti per-run. Non vengono quindi attribuiti
retrospettivamente:

- provider e modello usati per generazione e popolamento;
- revisione software certa e stato clean/dirty del working tree;
- `research_mode`;
- `population_mode` e possibile fallback;
- hash delle sorgenti acquisiti prima della generazione;
- manifesto di protocollo originale per ciascun run.

Il reflog colloca probabilmente la revisione
`08f5897c6b44b8fbf5e8630df367a5f6e3b7712d` nell'intervallo temporale dei run,
ma questa è registrata soltanto come inferenza `probable_not_observed`; lo stato
dirty del working tree è ignoto.

## Rivalutazione RQ2 secondaria

I 30 database sono stati rivalutati con il codice corrente, usando schema gold,
ground truth e sorgenti storiche recuperate insieme alle specifiche correnti di
osservabilità ed equivalenza funzionale. Questi risultati non ricostruiscono le
condizioni di esecuzione originarie e non vanno combinati con la matrice RQ2
strutturata.

| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali | Equivalenti |
|---|---|---:|---:|---:|---:|---:|---:|
| University | baseline | 5 | 0.9333 | 0.9333 | 0.9333 | 0.8200 | 4/5 |
| University | full_llm | 5 | 0.7000 | 0.6697 | 0.6721 | 0.4200 | 0/5 |
| Library | baseline | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| Library | full_llm | 5 | 1.0000 | 1.0000 | 1.0000 | 0.5000 | 0/5 |
| Hospital | baseline | 5 | 1.0000 | 1.0000 | 1.0000 | 0.9800 | 4/5 |
| Hospital | full_llm | 5 | 0.7500 | 0.7500 | 0.7500 | 0.4000 | 0/5 |

## Artefatti e riproduzione

Il bundle è in
`backend/reports/benchmark_rq1_expert_linked_recovered_20261113/` e contiene:

- snapshot dei record benchmark e del pacchetto RQ1 storico;
- i 30 database e schemi associati;
- le sorgenti storiche deduplicate e il collegamento ai 100 record documento;
- valutazione cell-level, ledger e query funzionali per ogni run;
- manifesti per-run e manifesto globale con SHA-256;
- `RECOVERY_COMPLETE.json`, scritto solo dopo il completamento.

Il database applicativo storico completo non è redistribuito perché contiene
progetti e documenti estranei alla matrice. Il bundle include soltanto un indice
sanitizzato dei 30 progetti pertinenti; l'hash del database sorgente è registrato
nel manifesto.

Per rigenerare il bundle da una copia autorizzata degli artefatti storici:

```powershell
cd tecnia-research
backend\.venv\Scripts\python.exe backend\recover_expert_linked_matrix.py `
  --source-backend <vecchia-copia>\backend `
  --output backend\reports\benchmark_rq1_expert_linked_recovered_20261113 `
  --datasets-root data\datasets `
  --current-expert-package backend\reports\rq1_expert_package
```

`--overwrite` accetta soltanto una directory figlia di `backend/reports` già
riconoscibile tramite il manifesto o il marker di recupero; non può cancellare
la directory dei report o il pacchetto esperti.
