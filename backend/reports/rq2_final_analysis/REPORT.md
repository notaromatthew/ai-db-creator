# RQ2 — analisi finale esplorativa della matrice a 30 run

## Ambito

L'analisi combina la matrice strutturata completa e l'adjudication umana
conclusa. Le unità statistiche per F1 e query funzionali sono i 30 run, cinque
per ogni combinazione dataset-condizione. I 1.294 record dell'adjudication sono
invece discrepanze già segnalate dal valutatore automatico e non vengono usati
come osservazioni indipendenti per sostituire le metriche per-run.

I confronti `baseline` contro `full_llm` sono esplorativi. Per ogni dataset e
metrica sono riportati differenza media, bootstrap percentile al 95% con seed
fisso, Hedges g, test di permutazione esatto e correzione di Holm sui sei
confronti post-hoc.

## Risultati per condizione

| Dataset | F1 baseline | F1 full_llm | Differenza full_llm-baseline | p esatto | p Holm |
| --- | ---: | ---: | ---: | ---: | ---: |
| University | 0,9638 | 0,6651 | -0,2987 | 0,0079 | 0,0476 |
| Library | 0,9348 | 0,9848 | +0,0500 | 1,0000 | 1,0000 |
| Hospital | 0,9496 | 0,6427 | -0,3068 | 0,0079 | 0,0476 |

Le differenze F1 sono quindi compatibili con una prestazione inferiore di
`full_llm` in University e Hospital in questa matrice. Library non segue lo
stesso pattern: il suo F1 è alto in entrambe le condizioni e leggermente più
alto in `full_llm`.

| Dataset | Query baseline | Query full_llm | Differenza | p esatto | p Holm |
| --- | ---: | ---: | ---: | ---: | ---: |
| University | 0,44 | 0,36 | -0,08 | 0,5476 | 1,0000 |
| Library | 0,62 | 0,40 | -0,22 | 0,0476 | 0,1905 |
| Hospital | 0,42 | 0,20 | -0,22 | 0,0476 | 0,1905 |

Nessun confronto sulle query funzionali resta sotto 0,05 dopo la correzione di
Holm. Con cinque run per cella, l'assenza di evidenza corretta non dimostra
equivalenza fra condizioni.

## Relazione fra F1 ed equivalenza funzionale

Sui 30 run, la correlazione di Spearman fra F1 e tasso di query funzionali è
0,490 (`p=0,006`). Nei singoli dataset è positiva ma più incerta: Hospital
0,614 (`p=0,059`), Library 0,577 (`p=0,081`) e University 0,547 (`p=0,102`).
Il risultato aggregato non autorizza a usare F1 come sostituto della verifica
funzionale: nessuno dei 30 run supera la regola binaria completa e Library
`full_llm` combina F1 medio 0,9848 con solo il 40% di query superate.

## Adjudication

La revisione finale classifica 967 discrepanze come errori, 4 come
rappresentazioni equivalenti, 12 come gold ambiguo e 311 come non
determinabili. Il risultato rafforza la validità della maggior parte dei flag
valutabili, ma i 311 casi non determinabili limitano soprattutto l'analisi
`full_llm` con schema divergente.

## Limiti

- cinque run per cella e confronti post-hoc esplorativi
- sorgenti eterogenee caricate insieme, quindi nessun effetto causale del formato
- esecuzione distribuita su due giorni con 2–3 run per cella e giorno
- adjudication applicata ai soli flag, non a un campione di celle corrette
- 311 discrepanze non determinabili dai soli artefatti ciechi mostrati

Gli output machine-readable sono `rq2_final_analysis.json`,
`rq2_condition_comparisons.csv` e `manifest.json`.
