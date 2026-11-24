# Stato di completamento della ricerca

## Sintesi

Le analisi RQ0, RQ1, RQ2 e RQ3 sono completate sui dati disponibili. RQ4 è
stata rimossa dal perimetro empirico della ricerca. NASA-TLX e SUS restano
esclusi dal protocollo corrente.

## RQ0 e RQ3

- pilot operativo: 5 sessioni completate;
- studio principale: 102 casi validi, 34 per braccio;
- valutazione cieca: 102 outcome collegati;
- successo del compito: 100% in tutti i bracci;
- nessuna differenza negli outcome primari dopo correzione di Holm;
- AI + Interfaccia più veloce del Manuale di 13,50 minuti in media;
- AI + Interfaccia più veloce di AI-only di 2,12 minuti in media;
- analisi riproducibile in `backend/analyze_available_records.py`;
- risultati in `backend/reports/user_study_available_records_20261124/`.

## RQ1

- analisi delle 45 valutazioni degli studenti;
- replica separata con tre esperti;
- controllo di integrità, accordo e risultati riproducibili;
- attestazione dell'indipendenza dei tre esperti.

## RQ2

- matrice strutturata da 30 run completata;
- verifica cieca e consenso su 1.294 discrepanze;
- metriche cell-level e query funzionali;
- matrice separata CSV/XLSX/TXT/PDF con 38 successi primari su 40;
- recovery post-outcome dei due fallimenti mantenuta come sensibilità separata;
- analisi finale e indice degli artefatti riproducibili completati.

## Paper

Il manoscritto contiene i risultati osservati RQ0--RQ3, la discussione e la
conclusione. La revisione scientifica e linguistica finale è completata; le
citazioni sono risolte e il PDF di 19 pagine è stato ricompilato e verificato
visivamente. Non restano segnaposto sperimentali. Rimangono esclusivamente
autori, affiliazioni, sede di pubblicazione e adeguamento allo stile editoriale
della sede scelta.

## Verifica tecnica

- suite backend completa: 605 test superati;
- un test saltato perché verifica uno script POSIX non eseguibile su Windows;
- nessun test fallito;
- dieci warning provenienti da dipendenze esterne, senza errori applicativi;
- compilazione LaTeX senza riferimenti, citazioni o box fuori margine.
