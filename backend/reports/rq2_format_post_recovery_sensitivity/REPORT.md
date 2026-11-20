# RQ2 — sensibilità post-recovery per formato

**Analisi secondaria post-outcome.** I due retry non sostituiscono gli outcome della matrice primaria, che resta 38/40.
Hash combinato degli input primari e di recovery: `d648aff8bfc67df73d2892e53858e956563084b503d9f487d977b6f625cc2e01`.

| Formato | Condizione | Primaria OK/totale | Post-recovery OK/totale | F1 post-recovery | Query post-recovery |
|---|---|---:|---:|---:|---:|
| csv | baseline | 5/5 | 5/5 | 1.0000 | 1.0000 |
| csv | full_llm | 4/5 | 5/5 | 0.6667 | 0.4000 |
| xlsx | baseline | 5/5 | 5/5 | 1.0000 | 1.0000 |
| xlsx | full_llm | 4/5 | 5/5 | 0.6667 | 0.4000 |
| txt | baseline | 5/5 | 5/5 | 1.0000 | 1.0000 |
| txt | full_llm | 5/5 | 5/5 | 0.6667 | 0.4000 |
| pdf | baseline | 5/5 | 5/5 | 1.0000 | 1.0000 |
| pdf | full_llm | 5/5 | 5/5 | 0.6667 | 0.4000 |

Tutti i 40 run dispongono di un database riuscito nell'overlay post-recovery. Le metriche restano identiche entro condizione e formato: baseline F1 1,0000 e full-LLM F1 0,6667; query funzionali rispettivamente 1,0000 e 0,4000. Il recovery elimina soltanto la differenza descrittiva di successo tecnico.

Questa stabilità supporta una conclusione di robustezza sul campione osservato, non una stima primaria 40/40 né equivalenza generale tra formati. La selezione dei retry è condizionata ai fallimenti osservati.
