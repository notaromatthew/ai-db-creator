# Pilot tecnico RQ2 e stato della matrice corretta — 5 novembre 2026

> **Stato:** questo documento non contiene ancora risultati primari confermativi.
> La prima matrice completa ha rivelato un'incompatibilità del client con le
> risposte Gemini a blocchi ed è conservata come pilot tecnico. La matrice v2 è
> completa (30/30), ma la quota del provider si è esaurita durante la ripresa
> dei run finali e confonde Hospital `full_llm` con l'ordine di esecuzione.
>
> La matrice storica collegata alle valutazioni RQ1 è stata successivamente
> recuperata, ma non sostituisce le matrici RQ2 di questo documento. Per RQ2 è
> classificata come rivalutazione storica secondaria perché priva dei manifesti
> originari per-run; vedere `docs/22-rq1-expert-linked-matrix-recovery.md`.

## Pilot OpenRouter del 6 novembre 2026

Un pilot separato ha verificato `nvidia/nemotron-3.5-super-vl:free` tramite
OpenRouter, con reasoning disabilitato, temperatura `0.1`, limite di output
4096 token, timeout 120 secondi e zero retry. La singola run
University `full_llm` è terminata senza fallback in circa 33 secondi e ha
prodotto 74 istruzioni SQL. Le metriche osservate sono precisione `0.8333`,
recall `0.6737`, F1 `0.6899` e tasso di query funzionali `0.3000`; la regola
binaria di equivalenza funzionale non è superata. Il bundle è in
`backend/reports/benchmark_openrouter_nemotron35_supervl_smoke_20261106/` e
gli hash degli artefatti verificano senza discrepanze.

Questo risultato dimostra la fattibilità tecnica del modello gratuito, non una
stima prestazionale: contiene una sola ripetizione, usa un provider e un modello
diversi dalla matrice Gemini e non deve essere aggregato con essa.

È stato poi eseguito un recovery selettivo, separato, degli undici run Gemini
con `status=error`. Nemotron ha completato otto run e ne ha falliti tre, tutti
Hospital `full_llm`, per output dello schema non parsabile. Gli aggregati
condizionati ai run riusciti sono: University `full_llm` F1 `0.6763` e query
funzionali `0.3000`; Library `full_llm` F1 `0.7348` e query `0.3000`; Hospital
baseline F1 `0.2369` e query `0.0000`; Hospital `full_llm` F1 `0.4783` e query
`0.0000`. Gli undici manifest e 57 hash di artefatto verificano senza errori.

Il recovery è una sensibilità al provider selezionata sui precedenti fallimenti:
non è un campione casuale, non stima direttamente le prestazioni complessive e
non può essere combinato con i 19 successi Gemini. La directory è
`backend/reports/benchmark_openrouter_nemotron35_supervl_selective_retry_20261106/`
e `recovery_manifest.json` registra la regola di selezione e la configurazione.

Il 7 novembre 2026 sono stati ritentati esclusivamente i tre errori Hospital
`full_llm` (run 2, 3 e 4), con ripresa fail-only e configurazione invariata.
Tutti e tre hanno nuovamente fallito durante la generazione dello schema; gli
otto successi precedenti non sono stati rieseguiti né sovrascritti. Il tentativo
non aggiunge osservazioni prestazionali e i fallimenti non sono conteggiati come
F1 pari a zero. Parametri e outcome sono registrati in
`retry_attempt_20261107.json` nella stessa directory del recovery.

Dopo il reset giornaliero della quota è stata eseguita una verifica minima del
provider, terminata con successo, e i tre run sono stati ritentati singolarmente.
Il run 3 è riuscito, mentre i run 2 e 4 hanno raggiunto il modello ma hanno
restituito output dello schema non accettato dal parser. La cella Hospital
`full_llm` contiene quindi tre run riusciti e due errori; sui soli successi,
F1 medio `0.4792` e tasso medio di query funzionali `0.0000`. Il risultato
mostra variabilità stocastica della validità del formato e non dimostra una
causa legata alla quota per questi ultimi due errori. Il ledger separato è
`retry_after_quota_reset_20261107.json`.

Una sensibilità successiva ha applicato il contratto opt-in `schema-json-v2`
esclusivamente ai due errori residui, Hospital `full_llm` run 2 e 4. Entrambi
i run hanno completato schema, popolamento e valutazione: successo di parsing
2/2 contro 0/2 negli ultimi
tentativi legacy sugli stessi indici. Sui due run selezionati, F1 medio `0.4802`
e query funzionali `0.0000`. Il risultato mostra che il vincolo JSON Schema
risolve questi due errori di formato, ma non migliora l'equivalenza funzionale.

I bundle registrano il contratto `schema-json-v2`, ma non il percorso parser
primario/repair locale. Non è quindi possibile stabilire retrospettivamente dai
soli artefatti se il repair sia intervenuto nei due successi.

La selezione è condizionata ai fallimenti precedenti e il contratto di output è
diverso: questi valori sono una sensibilità di robustezza e non vengono
aggregati con la matrice legacy. Protocollo e risultato sono in
`backend/reports/benchmark_openrouter_nemotron35_supervl_structured_retry_20261107/`.

## Matrice strutturata su due giorni: blocco 1

Il 7 novembre 2026 è stato completato il primo blocco preregistrato della nuova
matrice `schema-json-v2`: 15/15 run riusciti, senza errori né fallback. Tutti i
manifest registrano la stessa revisione `84bf74b33c54bbcb`, OpenRouter,
`nvidia/nemotron-3.5-super-vl:free`, `research_mode=true` e lo stesso contratto
di output. Sono stati verificati 97 hash di artefatto e 50 hash sorgente, senza
discrepanze; la scansione non ha trovato chiavi API nei report.

Gli aggregati intermedi condizionati ai successi sono: University baseline F1
`0.9935`, query `0.4667`; University `full_llm` F1 `0.6627`, query `0.3000`;
Library baseline F1 `0.9848`, query `0.7000`; Library `full_llm` F1 `0.9848`,
query `0.4000`; Hospital baseline F1 `0.9806`, query `0.5333`; Hospital
`full_llm` F1 `0.7430`, query `0.2000`.

Questi sono risultati intermedi con 2 o 3 repliche per cella. Le stime finali
richiedono il blocco pianificato dell'8 novembre; il giorno resta nella
provenienza e non viene rimosso dall'interpretazione. Il ledger del blocco è
`execution_day1_20261107.json` nella directory della matrice.

## Matrice strutturata su due giorni: risultato completo

Il blocco dell'8 novembre ha completato i quindici run rimanenti senza errori.
La matrice finale contiene 30/30 run riusciti, tutti con `population_mode=llm`,
zero fallback, una sola revisione software e configurazione uniforme. La
verifica finale copre 195 hash di artefatto, 100 hash sorgente e 30 hash delle
specifiche di valutazione, senza file mancanti o discrepanze.

| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali |
|---|---|---:|---:|---:|---:|---:|
| University | baseline | 5 | 0.9983 | 0.9402 | 0.9638 | 0.4400 |
| University | full_llm | 5 | 0.6667 | 0.6636 | 0.6651 | 0.3600 |
| Library | baseline | 5 | 0.9500 | 0.9213 | 0.9348 | 0.6200 |
| Library | full_llm | 5 | 1.0000 | 0.9713 | 0.9848 | 0.4000 |
| Hospital | baseline | 5 | 0.9996 | 0.9312 | 0.9496 | 0.4200 |
| Hospital | full_llm | 5 | 0.6496 | 0.6364 | 0.6427 | 0.2000 |

La riuscita tecnica non equivale all'equivalenza funzionale: nessuna cella
raggiunge in media il 100% delle query, e `full_llm` resta inferiore alla
baseline in University e Hospital. Library `full_llm` ottiene F1 elevato ma
solo il 40% delle query funzionali, confermando che similarità cell-level e
utilità funzionale misurano proprietà differenti.

Il blocco del secondo giorno mostra F1 inferiore in quattro celle su sei; le
differenze giorno 2 meno giorno 1 sono `-0.0743` University baseline, `+0.0040`
University `full_llm`, `-0.0833` Library baseline, `0.0000` Library `full_llm`,
`-0.0776` Hospital baseline e `-0.1672` Hospital `full_llm`. Sono descrittive,
con 2–3 run per giorno/cella, e indicano possibile deriva del provider senza
dimostrarne la causa. La matrice resta una sensibilità esplorativa separata dai
run Gemini, dai pilot legacy e dai recovery selettivi.

I risultati finali e la provenienza sono congelati in `execution_complete.json`
nella directory della matrice.

## Matrice separata per formato

Il 20 novembre 2026 è stata completata la matrice controllata sulla fixture
`format_equivalence`, che rappresenta gli stessi 45 fatti in CSV, XLSX, TXT e
PDF. Il protocollo è stato congelato prima del primo outcome: Google Gemini
Developer API, `gemini-3.5-flash-lite`, temperatura `0.1`, 8192 token, timeout
120 secondi, zero retry, concorrenza 1 e massimo 8 richieste/minuto. Sono
presenti tutti i 40 run previsti (quattro formati, due condizioni, cinque
repliche): 38 sono riusciti con `population_mode=llm` e senza fallback. Due run
`full_llm`, CSV run 1 e XLSX run 3, sono falliti durante la generazione dello
schema. Non è stato registrato alcun errore di quota e Nemotron non è stato
usato.

| Formato | Condizione | OK/totale | F1 sui successi | Query funzionali | Equivalenti |
|---|---|---:|---:|---:|---:|
| CSV | baseline | 5/5 | 1.0000 | 1.0000 | 5/5 |
| CSV | full-LLM | 4/5 | 0.6667 | 0.4000 | 0/4 |
| XLSX | baseline | 5/5 | 1.0000 | 1.0000 | 5/5 |
| XLSX | full-LLM | 4/5 | 0.6667 | 0.4000 | 0/4 |
| TXT | baseline | 5/5 | 1.0000 | 1.0000 | 5/5 |
| TXT | full-LLM | 5/5 | 0.6667 | 0.4000 | 0/5 |
| PDF | baseline | 5/5 | 1.0000 | 1.0000 | 5/5 |
| PDF | full-LLM | 5/5 | 0.6667 | 0.4000 | 0/5 |

Tra i run riusciti non emerge una differenza di accuratezza fra formati. Il
successo tecnico è descrittivamente inferiore di 0,20 per CSV e XLSX rispetto
a TXT e PDF nella condizione `full_llm`, ma tutti i confronti esatti di Fisher
corretti con Holm hanno `p=1.0000`. Con una sola fixture, cinque repliche per
cella e variabilità metrica nulla, il risultato è esplorativo e non dimostra
equivalenza generale fra formati. Artefatti e analisi sono in
`backend/reports/benchmark_format_equivalence_google_gemini35flashlite_20261120/`
e `backend/reports/rq2_format_analysis/`.

## Analisi statistica esplorativa e adjudication finale

I confronti post-hoc tra condizioni usano i cinque run di ciascuna cella,
test di permutazione esatti, differenze medie bootstrap con seed fisso, Hedges
g e correzione di Holm sui sei confronti dataset-per-metrica. Non costituiscono
un'analisi confermativa preregistrata.

Per F1, le differenze `full_llm - baseline` sono `-0,2987` in University
(`p` esatto `0,0079`, Holm `0,0476`), `+0,0500` in Library (`p=1,0000`) e
`-0,3068` in Hospital (`p` esatto `0,0079`, Holm `0,0476`). Per il tasso di
query funzionali, le differenze sono `-0,08`, `-0,22` e `-0,22`; nessuna resta
sotto `0,05` dopo Holm. Questi risultati supportano una differenza F1 nella
matrice osservata per University e Hospital, non una superiorità generale
della baseline per ogni dataset o metrica.

La correlazione di Spearman tra F1 e query funzionali sui 30 run è `0,490`
(`p=0,006`). Nei singoli dataset è positiva ma più incerta (`p` tra `0,059` e
`0,102`). Il dato aggregato non rende le due misure intercambiabili: nessun run
supera la regola binaria completa e Library `full_llm` combina F1 `0,9848` con
solo il 40% di query superate.

I due revisori hanno completato indipendentemente le 1.294 discrepanze della
matrice; 967 giudizi coincidevano e 327 sono stati risolti mediante consenso
cieco. Le decisioni finali sono 967 errori, 4 rappresentazioni equivalenti, 12
gold ambigui e 311 non determinabili. Escludendo ambigui e non determinabili,
967/971 flag valutabili sono errori confermati. Questa è una misura di validità
dei flag già selezionati, non l'accuratezza globale delle celle. Script, output
e hash riproducibili sono in `backend/reports/rq2_final_analysis/` e
`backend/reports/rq2_adjudication_completed/`.

## Configurazione e provenienza

Il pilot tecnico contiene 30 run: tre dataset, due condizioni e cinque
ripetizioni, con sorgenti eterogenee caricate insieme (`combined`). È stata
eseguita con Google Gemini Developer API, modello
`gemini-3.5-flash-lite`, temperatura `0.1`, concorrenza `1`, limite globale di
10 richieste/minuto e senza LLM-as-judge. Il passaggio dal modello 2.5 al 3.5 è
documentato nell'emendamento pre-outcome di `docs/20-rq2-functional-equivalence-protocol.md`.

Gli artefatti del pilot si trovano in
`backend/reports/benchmark_gemini35_observable_t01/`. Tutti i 30 run hanno un
manifest. La verifica del 5 novembre 2026 ha ricalcolato gli hash di ogni
artefatto elencato: 0 discrepanze. Tutti i manifest registrano lo stesso
provider, modello e temperatura. La matrice candidata corretta è in
`backend/reports/benchmark_gemini35_observable_t01_v2/`: contiene 30 manifest
e la verifica finale ha rilevato zero file mancanti o hash discordanti.
Non costituisce tuttavia un'unica esecuzione software omogenea: 23 manifest
registrano la revisione `80bd7a7a8f4d5657` e i sette run Hospital finali la
revisione `a99831587da569be`. Tutti i manifest registrano inoltre
`research_mode=false`. Nove fallimenti avvenuti durante la generazione dello
schema hanno `source_files` vuoto, perché questa versione del runner acquisiva
la provenienza degli input solo dopo quella fase. Questi limiti non sono stati
corretti retroattivamente negli artefatti congelati.

## Completezza operativa

Nel pilot, dodici run su 30 hanno completato il popolamento full-LLM; 18 sono falliti.
Quattordici fallimenti derivano da una risposta di popolamento non utilizzabile,
con successivo fallback deterministico, e quattro da uno schema non analizzabile.
I fallback sono conservati come artefatti. Queste cifre non sono risultati RQ2:
quattordici fallback sono almeno in parte attribuibili al bug poi corretto.

| Dataset | Condizione | Run LLM riusciti | Falliti | Tasso di successo |
|---|---|---:|---:|---:|
| University | baseline | 2 | 3 | 40% |
| University | full_llm | 1 | 4 | 20% |
| Library | baseline | 2 | 3 | 40% |
| Library | full_llm | 3 | 2 | 60% |
| Hospital | baseline | 1 | 4 | 20% |
| Hospital | full_llm | 3 | 2 | 60% |
| **Totale** | — | **12** | **18** | **40%** |

In una matrice tecnicamente valida, il tasso di successo è un risultato primario di affidabilità e deve essere
riportato accanto alle metriche condizionate. Non è lecito interpretare le
medie seguenti come prestazione attesa su tutti i tentativi.

## Accuratezza del pilot condizionata ai run riusciti

La tabella seguente si riferisce alla matrice v2 corretta. Diciannove run su 30
sono riusciti; nove hanno fallito durante la generazione dello schema e due
hanno prodotto un fallback di popolamento. Le medie sono condizionate ai soli
run riusciti.

| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali passate |
|---|---|---:|---:|---:|---:|---:|
| University | baseline | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| University | full_llm | 3 | 0.6667 | 0.6667 | 0.6667 | 0.5000 |
| Library | baseline | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Library | full_llm | 3 | 1.0000 | 1.0000 | 1.0000 | 0.5000 |
| Hospital | baseline | 3 | 0.9980 | 0.9685 | 0.9822 | 0.6333 |
| Hospital | full_llm | 0 | — | — | — | — |

Nella v2, tutti i run baseline University e Library risultano funzionalmente
equivalenti. Nessun run riuscito Hospital e nessun run
`full_llm` supera la regola binaria completa di equivalenza. Il caso Library
`full_llm` mostra perché le due misure vanno mantenute separate: F1 osservabile
perfetto, ma solo metà delle query funzionali passa in media.

## Limiti della matrice Gemini v2 storica

- Le sorgenti sono state caricate insieme: questo è uno scenario eterogeneo,
  non un confronto causale fra CSV, PDF, TXT e XLSX.
- Le medie usano solo 1–3 run riusciti per cella e sono descrittive. Gli
  intervalli `ci95_f1` presenti nei riepiloghi congelati applicano Wilson alla
  media degli F1 per-run, uso statisticamente non appropriato. Devono essere
  ignorati e non vanno presentati come inferenza; il runner successivo non li
  produrrà più.
- Il fallback non è un successo LLM. Una sensibilità separata potrà valutare la
  pipeline ibrida, senza mescolarla alla presente analisi.
- I lunghi output Hospital e Library hanno prodotto la maggior parte dei
  fallback; questa è un'osservazione dai log. L'attribuzione causale a lunghezza,
  formato della risposta o limite del client richiede un esperimento separato.
- L'adjudication umana cieca delle discrepanze critiche e dei conflitti tra F1
  ed equivalenza funzionale resta necessaria prima del testo definitivo.
- L'ordine del runner è bloccato per dataset e condizione. L'esaurimento quota
  ha colpito Hospital `full_llm`, eseguito per ultimo: il suo 0/5 non può essere
  attribuito alla condizione. Una replica richiede quota sufficiente e ordine
  interlacciato o randomizzato preregistrato.

## Stato dei passi successivi alla matrice Gemini v2

- Completato: directory storiche conservate senza aggregarle alla nuova matrice.
- Completato: replica `schema-json-v2` con una revisione, `research_mode=true`,
  ordine interlacciato e due blocchi quota preregistrati; 30/30 successi.
- Completato: sensibilità separata sul contratto strutturato e limite di output.
- Completato: paper aggiornato distinguendo osservazioni e limiti.
- Completato: fixture semanticamente equivalente CSV/XLSX/TXT/PDF con 45 fatti,
  validazione automatica e hash congelati in
  `data/datasets/format_equivalence/fixture_manifest.json`.
- Da eseguire: nuova matrice 4 formati x 2 condizioni x 5 repliche, dopo avere
  congelato provider, modello e revisione secondo
  `docs/25-rq2-format-comparison-protocol.md`.
- Completato: pacchetto cieco completo di 1.294 discrepanze, due ordini
  indipendenti, consenso sui 327 disaccordi e mappa privata ricongiunta dopo la
  chiusura; artefatti congelati in
  `backend/reports/rq2_blind_adjudication/`.
- Completato: analisi statistica esplorativa per condizione e integrazione
  dell'adjudication nel risultato finale.
