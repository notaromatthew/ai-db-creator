# RQ2 — confronto esplorativo fra formati

Matrice congelata: 4 formati × 2 condizioni × 5 run. Modello: `gemini-3.5-flash-lite`; temperatura 0.1.
Hash combinato degli input analizzati: `a6d3320b12f75f6e9bdd8381b9afb844ff70682bb9a9208091c78bdeb9421627`.

| Formato | Condizione | OK/totale | Successo tecnico | Precision | Recall | F1 | Query funzionali | Equivalenti |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| csv | baseline | 5/5 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| csv | full_llm | 4/5 | 80.0% | 0.6667 | 0.6667 | 0.6667 | 0.4000 | 0/4 |
| xlsx | baseline | 5/5 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| xlsx | full_llm | 4/5 | 80.0% | 0.6667 | 0.6667 | 0.6667 | 0.4000 | 0/4 |
| txt | baseline | 5/5 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| txt | full_llm | 5/5 | 100.0% | 0.6667 | 0.6667 | 0.6667 | 0.4000 | 0/5 |
| pdf | baseline | 5/5 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| pdf | full_llm | 5/5 | 100.0% | 0.6667 | 0.6667 | 0.6667 | 0.4000 | 0/5 |

## Interpretazione vincolata ai dati

Nei run riusciti non emerge una differenza di accuratezza fra formati: le metriche sono costanti all'interno di ciascuna condizione. La baseline raggiunge F1 1,0000 e il full-LLM F1 0,6667 in ogni formato osservabile. Questo non dimostra equivalenza generale fra formati: la fixture è singola, i run sono cinque per cella e la variabilità metrica osservata è nulla.

L'unica differenza osservata riguarda il successo tecnico. CSV e XLSX hanno un errore di generazione dello schema ciascuno; TXT e PDF completano 5/5 run. Tutti i confronti di Fisher corretti con Holm sono non significativi con questa numerosità. I fallimenti sono conservati come outcome e non sostituiti.

## Fallimenti

- `csv/full_llm`: 1 — LLMException: Schema generation failed
- `xlsx/full_llm`: 1 — LLMException: Schema generation failed

I risultati restano un'analisi esplorativa separata dalla matrice `combined` e non sono combinati con essa.
