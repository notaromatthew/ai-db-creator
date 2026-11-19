# Analisi RQ1 — valutazione degli schemi

## Stato del dataset

- Valutazioni: 1350
- Valutatori: 45
- Schemi: 30
- Scala: Likert 1-5
- SHA-256 sorgente: `0c73f534513d9330d1fffa951286edd2b00f153341df07f4a6a0fa537d2c7164`
- Commenti esclusi dall'analisi; nessuna risposta è marcata come imputata.
- Cinque timestamp mancanti sono metadati non usati negli outcome RQ1.

## Accordo fra valutatori

| Dimensione | Alpha ordinale | IC bootstrap 95% | Accordo esatto | Accordo adiacente |
|---|---:|---:|---:|---:|
| d1_3nf | 0.812 | [0.742, 0.855] | 20.0% | 30.0% |
| d2_naming | -0.018 | [-0.021, -0.014] | 13.3% | 43.3% |
| d3_constraints | 0.794 | [0.550, 0.855] | 10.0% | 23.3% |
| d4_relationships | 0.803 | [0.564, 0.867] | 10.0% | 23.3% |
| d5_domain | 0.775 | [0.536, 0.841] | 6.7% | 16.7% |
| overall | 0.791 | [0.653, 0.846] | 12.0% | 27.3% |

## Confronto primario fra condizioni

L'unità del confronto è lo schema: i 45 giudizi sono aggregati per schema prima del test, evitando di trattare 1.350 misure ripetute come indipendenti.

| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |
|---|---:|---:|---:|---:|---:|---:|
| d1_3nf | 4.364 | 4.871 | 0.507 | [0.221, 0.776] | 0.01348 | 1.233 |
| d2_naming | 4.956 | 4.956 | 0.000 | [-0.021, 0.022] | 1 | 0.000 |
| d3_constraints | 4.622 | 4.944 | 0.321 | [0.116, 0.572] | 0.07256 | 0.960 |
| d4_relationships | 4.330 | 4.944 | 0.613 | [0.221, 1.080] | 0.07256 | 0.959 |
| d5_domain | 4.618 | 4.938 | 0.320 | [0.117, 0.564] | 0.07256 | 0.975 |

## Deviazioni e limiti da riportare

- Il piano descriveva tre esperti; il dataset osservato contiene 45 valutatori.
- La scala effettiva e validata dall'applicazione è 1–5, non 0–4.
- I punteggi mostrano un forte effetto soffitto; distribuzioni e percentuale di 5 devono accompagnare medie e test.
- Le etichette osservate sono `baseline` e `full_llm`; la loro interpretazione deve rimanere coerente con il manifesto dei run originari.
- La sensibilità appaiata per dataset/run è esportata separatamente e non sostituisce il confronto primario pianificato.

Questo report è un artefatto analitico riproducibile, non una conferma retrospettiva della preregistrazione o dell'idoneità dei valutatori.
