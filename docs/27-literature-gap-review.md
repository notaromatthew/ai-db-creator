# Revisione mirata del gap di letteratura

## Stato

Questa è una ricerca mirata aggiornata al 19 novembre 2026. Non viene
presentata come revisione sistematica: una versione sistematica richiede almeno
una banca dati bibliografica istituzionale, esportazione dei risultati,
deduplicazione e screening documentato da revisori.

## Query utilizzate

- `LLM relational database schema generation natural language database design`
- `large language model database schema generation`
- `large language model database design schema generation`
- `LLM document information extraction relational database population`

Fonti consultate: arXiv, ACL Anthology e risultati primari indicizzati da ACM.
Sono stati esclusi i lavori limitati a text-to-SQL quando assumevano uno schema
già esistente.

La voce bibliografica precedentemente attribuita a “NL2Schema” con identificativo
arXiv `2310.05978` è stata rimossa: l'identificativo appartiene a un articolo
sui comportamenti degli utenti in reti basate sul volontariato e non supporta
alcuna affermazione sulla generazione di schemi.

## Lavori direttamente rilevanti

| Lavoro | Schema | Popolamento | Documenti | UI/HITL | Differenza rispetto ad AI-DB-Creator |
| --- | --- | --- | --- | --- | --- |
| SchemaAgent (2025) | sì, incl. 3NF | no | requisiti testuali | no | benchmark e generazione multi-agente dello schema |
| SQUiD (EMNLP 2025) | sì | sì | testo non strutturato | no | confronto end-to-end più vicino; pipeline neuro-simbolica |
| SchemaBridge (2026) | sì, valutazione | no | requisiti testuali | no | benchmark di fedeltà e sotto-specificazione dello schema |
| SynSQL (2026) | schema selezionato | sì | domanda + schema | no | genera database per valutare text-to-SQL, non per utenti finali |

## Correzione del gap

Non è più sostenibile affermare che nessun lavoro generi e popoli un database
relazionale a partire da testo: SQUiD copre esplicitamente entrambe le fasi. Il
contributo differenziale di AI-DB-Creator va formulato come combinazione di:

- sorgenti eterogenee CSV/XLSX/PDF/TXT
- revisione visuale e modifica diretta di schema e dati
- strategia deterministic-first con fallback LLM
- provenance, manifesti, hash e query funzionali
- confronto sperimentale Manuale / AI-only / AI+UI
- analisi dei log di interazione dei non esperti

## Passo necessario per la versione sistematica

Eseguire le query su Scopus, Web of Science o ACM Digital Library con intervallo
temporale e criteri di inclusione congelati. Conservare export, conteggi prima e
dopo deduplicazione, motivi di esclusione e tabella di estrazione. Il testo del
paper mantiene esplicitamente questa limitazione.
