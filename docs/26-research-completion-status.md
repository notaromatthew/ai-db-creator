# Stato di completamento della ricerca

## Sintesi

La parte automatizzabile di RQ1 e della matrice RQ2 principale è stata
eseguita e resa riproducibile. RQ0, RQ3 e RQ4 dipendono ancora dalla raccolta
con partecipanti. Il confronto controllato fra formati RQ2 è stato completato
come analisi esplorativa su 40 run con protocollo, provider, modello e revisione
software congelati prima del primo outcome.

## Completato

### RQ1

- analisi delle 45 valutazioni degli studenti
- replica separata con tre esperti
- controllo di integrità, accordo e risultati riproducibili
- attestazione dell'indipendenza dei tre esperti

Resta da acquisire l'attestazione esplicita che il terzo esperto fosse cieco
alla condizione, se questo fatto è vero e documentabile. Non può essere inferito
dai punteggi.

### RQ2

- audit di osservabilità dei tre dataset
- matrice strutturata `3 dataset x 2 condizioni x 5 run`, 30/30 successi
- verifica di 195 hash artefatto, 100 hash sorgente e 30 hash delle specifiche
- metriche cell-level e query funzionali per ogni run
- pacchetto cieco di 1.294 discrepanze
- due revisioni indipendenti e consenso sui 327 disaccordi
- ledger finale ricongiunto alla mappa privata dopo il consenso
- confronto esplorativo `baseline`/`full_llm`, test esatti e correzione di Holm
- analisi della correlazione fra F1 ed equivalenza funzionale
- matrice separata CSV/XLSX/TXT/PDF: 40 run pianificati, 38 successi senza
  fallback e due fallimenti di generazione conservati come outcome
- analisi esplorativa per formato con confronti esatti e correzione di Holm

Gli output finali sono in:

- `backend/reports/rq2_adjudication_completed/`
- `backend/reports/rq2_final_analysis/`
- `docs/21-rq2-primary-results.md`
- `backend/reports/rq2_format_analysis/`

### Infrastruttura per RQ0/RQ3/RQ4

- protocollo a tre bracci
- materiali e runbook per i partecipanti
- logging pseudonimizzato delle interazioni
- analizzatore congelato per outcome e pattern di interazione
- NASA-TLX e SUS esclusi dal protocollo corrente come richiesto

## Attività automatizzabili ancora disponibili

### Repliche RQ2 opzionali

La matrice RQ2 per formato è conclusa. Eventuali repliche con Nemotron o altri
modelli devono essere nuove matrici complete e separate, non sostituzioni dei
due fallimenti Gemini. Non sono necessarie per chiudere l'analisi corrente.

### Analisi dopo la raccolta partecipanti

Quando saranno disponibili gli export pseudonimizzati, gli script preparati
potranno produrre automaticamente:

- confronti Manuale vs AI+UI per RQ0
- confronti AI-only vs AI+UI per RQ3
- errori residui ed effect size
- frequenze e sequenze di modifica per RQ4
- correlazioni e clustering esplorativo dei pattern di interazione

## Attività necessariamente umane

- validazione indipendente finale dei gold standard
- eventuale conferma documentale della cecità del terzo esperto RQ1
- scelta di autori, affiliazioni e sede editoriale
- revisione sistematica della letteratura e valutazione qualitativa dei lavori
- archiviazione dell'eventuale comunicazione istituzionale sull'approvazione etica
- pilot formativo con 5--8 partecipanti
- reclutamento e conduzione dell'esperimento a tre bracci
- interpretazione finale integrata di RQ0--RQ4 e approvazione del manoscritto

## Stato del paper

Le sezioni osservate RQ1 e RQ2 sono aggiornate. Restano segnaposto espliciti
per revisione della letteratura, reclutamento, risultati RQ0/RQ3/RQ4 e
discussione generale. Questi segnaposto non devono essere riempiti con dati
sintetici o inferenze non osservate.
