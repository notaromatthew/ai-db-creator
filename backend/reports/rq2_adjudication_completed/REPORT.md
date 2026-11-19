# RQ2 — verifica indipendente e consenso

## Stato

I due fogli completati superano i controlli di integrità del protocollo
`rq2_blind_adjudication_v1`:

- 1.294 elementi presenti in ciascun foglio
- nessun ID mancante o duplicato
- corrispondenza completa con la mappa privata
- valori di decisione e confidenza ammessi
- note presenti nei casi in cui il protocollo le richiede
- nessuna differenza tra i due fogli nei campi osservativi mostrati ai revisori

La fase di consenso è **completa**. Tutte le 327 decisioni controverse hanno
una decisione finale e una motivazione; gli ID e tutti i campi osservativi
coincidono con il pacchetto congelato.

## Accordo indipendente

- accordi esatti: 967/1.294 (74,7%)
- accordo atteso dalle distribuzioni marginali: 76,6%
- kappa di Cohen nominale: -0,081
- disaccordi: 327/1.294 (25,3%)

Tutti i 967 accordi sono classificazioni `errore | errore`. Il kappa negativo non
contraddice l'accordo percentuale: le distribuzioni sono fortemente sbilanciate
verso `errore`, quindi l'accordo atteso dalle marginali supera leggermente quello
osservato. Il risultato segnala che le categorie di incertezza ed equivalenza
sono state applicate in modo diverso e rende necessaria la fase di consenso.

## Struttura dei disaccordi

| Revisore A | Revisore B | Conteggio |
| --- | --- | ---: |
| errore | non determinabile | 225 |
| non determinabile | errore | 60 |
| rappresentazione equivalente | errore | 26 |
| gold ambiguo | errore | 12 |
| gold ambiguo | rappresentazione equivalente | 4 |

## Esito finale

| Decisione finale | Conteggio | Quota delle discrepanze |
| --- | ---: | ---: |
| errore | 967 | 74,7% |
| rappresentazione equivalente | 4 | 0,3% |
| gold ambiguo | 12 | 0,9% |
| non determinabile | 311 | 24,0% |

Escludendo i casi `gold ambiguo` e `non determinabile`, 967 delle 971
discrepanze valutabili sono errori confermati (99,6%). Questa percentuale
descrive esclusivamente i record già segnalati dal confronto automatico: non è
precision, recall o F1 a livello di cella e non ne sostituisce i valori.

### Per condizione

| Condizione | Discrepanze | Errore | Equivalente | Gold ambiguo | Non determinabile |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 366 | 362 | 4 | 0 | 0 |
| full_llm | 928 | 605 | 0 | 12 | 311 |

I 311 casi non determinabili sono concentrati in University full-LLM (225) e
Hospital full-LLM (86). Il ledger finale conserva la decisione di ciascun
revisore, la risoluzione, la decisione finale e la mappa privata ricongiunta
soltanto dopo la chiusura del consenso.

## Artefatti finali

- `final_adjudication_ledger.csv`: ledger completo delle 1.294 discrepanze
- `final_adjudication_summary.json`: riepilogo complessivo e per dataset,
  condizione e run
- `final_manifest.json`: hash degli input e degli output finali
- `agreement_summary.json`: accordo prima del consenso

I file originali non sono stati modificati. Gli hash SHA-256 degli input e della
mappa privata sono registrati nei riepiloghi; non sono registrati o pubblicati
tempi di compilazione.
