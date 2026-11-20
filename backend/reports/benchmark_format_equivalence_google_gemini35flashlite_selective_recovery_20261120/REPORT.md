# RQ2 — recovery selettivo dei due fallimenti Gemini

Il 20 novembre 2026 sono stati ripetuti, in directory separate, esclusivamente
i due run `full_llm` falliti nella matrice primaria:

| Formato | Run | Esito primario | Esito recovery | F1 | Query funzionali | Equivalente |
|---|---:|---|---|---:|---:|---|
| CSV | 1 | errore | riuscito | 0.6667 | 0.4000 | no |
| XLSX | 3 | errore | riuscito | 0.6667 | 0.4000 | no |

Entrambi i recovery hanno usato Google Gemini
`gemini-3.5-flash-lite`, temperatura `0.1`, massimo 8192 token, timeout 120
secondi, zero retry applicativi, `research_mode=true` e popolamento full-LLM
senza fallback. Non è stato registrato alcun errore di quota e Nemotron non è
stato usato.

La matrice primaria registra la revisione Git `0d225aabf6a01ac61d39223df3461e83db1c9170`,
mentre i recovery registrano `a680691a9f67fa37dc685eff3b3a787ffc288ea9`,
il commit che ha aggiunto risultati, analisi e documentazione della matrice. La
revisione software sperimentale resta identica (`b08c17b85053fd3a`), indicando
che la pipeline usata per generazione e valutazione non è cambiata.

I due successi mostrano che i fallimenti originari erano recuperabili con una
nuova generazione, ma non ne identificano retrospettivamente la causa. La
matrice primaria resta immutata e viene riportata come 38/40: questi tentativi
sono una sensibilità selezionata sui fallimenti e non vengono inseriti nelle
stime primarie o nei confronti per formato.

Nei due manifest locali `runs_per_cell` vale 3 perché `--runs` è rimasto al
default del CLI; `run_indices` è l'elemento operativo e registra rispettivamente
solo `[1]` e `[3]`. Il campo non ha modificato prompt, generazione o valutazione,
ma la differenza rispetto al valore 5 della matrice primaria è dichiarata per
trasparenza.
