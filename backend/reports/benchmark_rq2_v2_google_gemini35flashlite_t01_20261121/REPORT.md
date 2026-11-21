# Matrice RQ2 v2 completa

30/30 run riusciti, tutti con popolamento LLM e senza fallback.

| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali | Equivalenti |
|---|---|---:|---:|---:|---:|---:|---:|
| Hospital | baseline | 5 | 0.5000 | 0.4296 | 0.4475 | 0.0600 | 0/5 |
| Hospital | full_llm | 5 | 0.3000 | 0.2663 | 0.2819 | 0.0000 | 0/5 |
| Library | baseline | 5 | 0.7500 | 0.7429 | 0.7464 | 0.3000 | 0/5 |
| Library | full_llm | 5 | 0.7500 | 0.7188 | 0.7333 | 0.2000 | 0/5 |
| University | baseline | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 5/5 |
| University | full_llm | 5 | 0.7000 | 0.6697 | 0.6721 | 0.4000 | 0/5 |

La matrice usa i gold standard `rq2_functional_v2` approvati da GOLD-A e GOLD-B. 
I risultati v1 sono storici e non vengono aggregati con questi valori.

Tutti i run condividono revisione software, provider, modello, temperatura, formato sorgente e contratto di output. 
L'esecuzione in un'unica sessione limita la separazione tra effetto del modello e possibile deriva temporale del provider.
