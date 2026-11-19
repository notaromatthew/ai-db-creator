# Protocollo RQ2: accuratezza osservabile ed equivalenza funzionale

## Stato e finalità

Questo documento congela la semantica dell'analisi RQ2 prima della
rigenerazione dei benchmark. Non contiene risultati. La versione machine-readable
del protocollo è `data/datasets/<dataset>/evaluation_spec.json`.

RQ2 mantiene due misure distinte:

1. **accuratezza a livello di cella**, limitata ai fatti presenti nei documenti
   forniti al sistema;
2. **equivalenza funzionale**, misurata mediante una suite di query e controlli
   di integrità, per non classificare come errore una rappresentazione relazionale
   diversa ma informativamente equivalente.

La seconda misura affianca e non sostituisce precision, recall e F1. Tutti i
punteggi continui devono essere pubblicati anche quando viene applicata una
soglia binaria.

## Audit di osservabilità dei dataset

L'audit dei generatori e dei documenti correnti ha rilevato che alcuni valori
del database gold non sono ricostruibili dagli input consegnati al sistema.
Questi valori non possono essere falsi negativi primari di estrazione.

| Dataset | Fatti osservabili | Fatti gold non osservabili dagli input correnti |
|---|---|---|
| University | 45 iscrizioni, 22 studenti presenti nelle iscrizioni, 8 corsi | 8 studenti gold che non compaiono in alcun documento |
| Library | 20 membri, 50 libri, 10 categorie, membro e date dei 60 prestiti | libro e identificativo del prestito; importo/stato/data delle multe |
| Hospital | 100 pazienti, 200 appuntamenti, medici e reparti citati negli appuntamenti | righe di trattamenti, farmaci, prescrizioni e fatture |

Questo è un difetto costruttivo del benchmark, non un risultato sul modello. Le
metriche storiche calcolate sull'intero gold devono essere etichettate come
**full-gold sensitivity analysis** e non come stima primaria dell'estrazione.

## Unità sperimentale e condizioni

- L'unità è un run indipendente per `dataset × formato × condizione`.
- `baseline` (schema gold + popolamento LLM) è la condizione primaria RQ2 perché
  isola il popolamento.
- `full_llm` è un'analisi end-to-end secondaria, poiché combina errori di schema,
  allineamento e popolamento.
- La configurazione primaria proposta è temperatura `0.1`, 5 run per cella,
  con modello, provider, `top_p`, token massimi e revisione software congelati
  nel manifest. Temperatura `0.5` è una sensibilità separata.
- Una temperatura bassa non garantisce identità byte-per-byte: i run ripetuti e
  i manifest servono a rendere visibile la non determinazione residua.

Le soglie e questa scelta devono essere approvate prima di ispezionare i nuovi
outcome. Se l'approvazione modifica il protocollo, la modifica riceve una nuova
versione; la versione precedente non viene sovrascritta.

### Emendamento del 5 novembre 2026: modello primario

La matrice primaria usa Google Gemini Developer API con
`gemini-3.5-flash-lite`. Il modello inizialmente previsto,
`gemini-2.5-flash-lite`, ha risposto prima di qualunque run riuscito che non è
più disponibile per nuovi utenti e ha indicato `gemini-3.5-flash-lite` come
sostituto. L'emendamento è stato quindi registrato prima dell'ispezione di
outcome primari; provider, modello e temperatura restano salvati in ogni
manifest. I tentativi tecnici falliti precedenti non entrano nell'analisi.

Per la ripresa della matrice corretta, i retry interni del client Gemini sono
impostati a zero (`GOOGLE_MAX_RETRIES=0`): un timeout o un errore 5xx viene
registrato come fallimento operativo del run e non trattiene indefinitamente la
coda. La modifica segue due interruzioni documentate in cui lo stesso payload
Hospital ha superato ripetutamente il timeout di 600 secondi; non modifica
prompt, temperatura, dati o criteri di valutazione.

La replica strutturata del 7–8 novembre 2026 ha applicato questo requisito con
`--schedule interleaved` e due blocchi quota preregistrati.
L'ordine interlacciato distribuisce deriva temporale e indisponibilità del
provider fra dataset e condizioni; il valore della schedulazione è parte della
configurazione congelata e non rende direttamente comparabile la replica con
la matrice v2 eseguita in ordine `blocked`.

## Confronto tra formati

I documenti correnti non permettono un confronto causale CSV/XLSX/PDF/TXT:
contengono fatti diversi e nessuno dei tre dataset contiene attualmente una
variante XLSX. Prima del confronto per formato deve esistere, per
ogni dataset, una fixture canonica di fatti osservabili resa in quattro formati
semanticamente equivalenti. La trasformazione non deve aggiungere o rimuovere
fatti, e ogni variante deve avere hash e conteggio atteso.

Il formato è analizzato solo quando il run riceve una variante alla volta. Un
run con CSV, PDF e TXT caricati insieme può essere riportato come scenario
eterogeneo, ma non attribuito a un singolo formato.

## Allineamento delle entità

L'allineamento segue questo ordine congelato:

1. corrispondenza esatta dopo normalizzazione del nome;
2. registro di alias versionato, definito senza consultare condition label o
   outcome;
3. chiavi naturali dichiarate in `evaluation_spec.json`;
4. adjudication cieca di due revisori per i soli casi irrisolti.

Gli identificativi sintetici possono differire. Non vengono considerati errori
se le entità sono univocamente allineabili mediante chiavi di business e le
relazioni risultano preservate. Se una tabella non possiede una chiave naturale
diretta, l'identità può essere definita da una query canonica che attraversa le
FK (per esempio email studente + codice corso + semestre).

## Canonicalizzazione dei valori

- Unicode: normalizzazione NFKC.
- Testo: trim e collasso degli spazi interni; confronto case-sensitive salvo
  email, codici e identificatori esplicitamente dichiarati case-insensitive.
- Numeri: confronto numerico; tolleranza assoluta `0.005` solo per importi.
- Date: conversione non ambigua a `YYYY-MM-DD`.
- Datetime: conversione a `YYYY-MM-DD HH:MM:SS`; nessuna conversione di fuso se
  il sorgente non dichiara un fuso.
- Booleani: insiemi espliciti di token veri e falsi.
- `NULL` ed empty string restano distinti.
- Ordine di righe e colonne non è semanticamente rilevante.

## Query funzionali

Ogni `evaluation_spec.json` contiene query SQL di sola lettura sullo schema gold.
Il runner applica l'allineamento congelato allo schema generato e confronta i
result set canonicalizzati. Le query coprono:

- inventario delle entità osservabili;
- attributi di business;
- join necessari a ricostruire le relazioni;
- conteggi e aggregazioni;
- casi con cardinalità uno-a-molti o molti-a-molti quando osservabili.

Per ogni query sono salvati SQL gold, SQL effettivamente eseguito sul database
generato, result hash, numero di righe, esito e differenze. Una query non
riscrivibile è un fallimento esplicito, non un risultato vuoto.

## Regola di equivalenza funzionale

La decisione binaria preregistrata è positiva solo se:

- passa il 100% delle query critiche;
- passa almeno il 90% di tutte le query;
- non esistono violazioni PK/FK o duplicati sulle chiavi naturali;
- nessuna entità di business osservabile critica è persa o aggiunta.

Devono essere riportati anche tasso di query superate, risultati per query,
violazioni e intervalli di confidenza. La soglia non converte una mancata
osservabilità in successo: i fatti fuori scope sono esclusi, non imputati.

## Ledger delle discrepanze

Il ledger automatico di ogni run conserva:

`dataset`, `format`, `condition`, `run`, `table`, `natural_key`, `column`,
`source_value`, `generated_value`, `gold_value`, `error_type`,
`source_document`, `source_location`, `alignment_method`.

I campi `source_value`, `source_document` e `source_location` restano vuoti
quando il percorso di estrazione non espone una provenienza a livello di cella;
non devono essere ricostruiti per inferenza. La loro compilazione richiede una
provenienza cell-level prodotta dalla pipeline o l'adjudication umana cieca.

Le categorie sono: exact, type-consistent, missing value, wrong value, misplaced
value, missing row, extra row, FK violation, type mismatch e not-observable.
`not-observable` non entra nei denominatori primari.

## Adjudication umana e LLM-as-judge

Due revisori indipendenti e ciechi a condizione, modello e punteggi esaminano:

- tutte le discrepanze critiche;
- tutti i conflitti tra F1 ed equivalenza funzionale;
- un campione casuale preregistrato delle altre discrepanze.

Le decisioni ammesse sono errore, rappresentazione equivalente, alias valido,
gold ambiguo o non determinabile. I disaccordi sono risolti per consenso e
conservati nel ledger. L'LLM-as-judge resta supplementare: non decide la metrica
primaria e non sostituisce i revisori.

Il pacchetto operativo congelato è in
`backend/reports/rq2_blind_adjudication/`. Contiene 1.294 discrepanze provenienti
da tutti i 30 run della matrice primaria. I due fogli dei revisori usano ordini
casuali distinti; condizione e run sono conservati soltanto nella mappa privata
del coordinatore. I due revisori hanno completato indipendentemente tutti i
1.294 elementi; 967 decisioni coincidevano e 327 sono state risolte mediante
consenso cieco. Il foglio di consenso ometteva condizione e run e la mappa
privata è stata riunita alle decisioni soltanto dopo la chiusura. Il ledger
finale contiene 967 errori, 4 rappresentazioni equivalenti, 12 casi con gold
ambiguo e 311 casi non determinabili. Questi conteggi descrivono i record di
discrepanza già segnalati e non sostituiscono precision, recall o F1 a livello
di cella.

## Pacchetto minimo per run

I progetti creati dal runner batch sono assegnati all'account tecnico
`research-benchmark-runner`. L'account rende esplicita la provenienza
automatizzata e soddisfa i vincoli di integrità applicativi; non rappresenta
un partecipante umano e va escluso dalle analisi degli utenti.

Un run primario RQ2 è riuscito solo quando `population_mode` è `llm`. Se la
chiamata al provider non restituisce SQL utilizzabile e la pipeline applica il
fallback deterministico, il database e i log sono conservati ma il run è
marcato come fallito e non entra nelle metriche aggregate.

Ogni directory di run deve essere autosufficiente e contenere:

- database generato e schema generato;
- report cell-level completo e ledger delle discrepanze;
- allineamento e risultati delle query funzionali;
- manifest con hash degli input/output, revisione Git e parametri LLM;
- elenco esatto dei documenti caricati e loro hash;
- errori o interruzioni, senza eliminare i run falliti.

I report aggregati non sostituiscono questi artefatti grezzi.

La provenienza delle sorgenti deve essere calcolata prima della prima chiamata
LLM, così che anche un fallimento di generazione dello schema conservi nomi e
hash degli input. Una matrice primaria deve inoltre usare una sola revisione
software e `research_mode=true`; riprese effettuate dopo modifiche al codice
sono pilot tecnici distinti o richiedono una deviazione esplicita.

Gli F1 per-run sono misure continue aggregate, non successi binomiali. Non si
applica pertanto l'intervallo di Wilson alla loro media. Finché non viene
preregistrata una procedura inferenziale adatta all'unità di analisi, il runner
riporta media, numerosità valutabile e range descrittivo, senza etichettarlo
come intervallo di confidenza.

## Reporting

La relazione finale separa:

1. accuratezza primaria sui fatti osservabili, per formato;
2. sensibilità full-gold, esplicitamente affetta da fatti non osservabili;
3. equivalenza funzionale per query;
4. scenario eterogeneo multi-documento;
5. `baseline` da `full_llm`;
6. analisi deterministica dall'adjudication supplementare.

## Sensibilità OpenRouter preregistrata il 6 novembre 2026

Prima di osservare gli outcome della matrice completa Nemotron è stata fissata
una sensibilità esplorativa indipendente: tre dataset, condizioni `baseline` e
`full_llm`, cinque repliche per cella, sorgenti `combined` e ordine
`interleaved`. Il provider è OpenRouter e il modello è
`nvidia/nemotron-3.5-super-vl:free`; temperatura `0.1`, reasoning disabilitato,
8192 token massimi di output, timeout 120 secondi, zero retry, concorrenza 1 e
massimo 10 richieste al minuto. La matrice usa una directory nuova e
`research_mode=true`.

Questa analisi non sostituisce né viene combinata con Gemini. Il passaggio da
4096 a 8192 token deriva dall'osservazione tecnica, nel pilot precedente, di
popolamenti Library e Hospital terminati esattamente al tetto di 4096 token.
La modifica è quindi una deviazione esplicita e rende la matrice completa non
direttamente aggregabile con quel pilot.

## Sensibilità del contratto JSON preregistrata il 7 novembre 2026

Dopo che Hospital `full_llm` run 2 e 4 hanno raggiunto OpenRouter ma prodotto
uno schema non accettato dal parser legacy, viene eseguito un retry esplorativo
separato con `schema-json-v2`. Provider, modello, temperatura, reasoning, limite
token e prompt restano invariati; cambia esclusivamente il contratto di risposta,
imposto tramite `response_format=json_schema`, con al massimo un'estrazione JSON
deterministica locale se il parser primario fallisce. Il comportamento è opt-in
con `OPENROUTER_SCHEMA_JSON_MODE=true` e il default storico resta invariato.

La selezione comprende soltanto Hospital `full_llm` run 2 e 4 e serve a valutare
la robustezza del formato. Gli outcome non devono essere aggregati ai run
`legacy-pydantic-v1`; configurazione e regola di selezione sono congelate in
`backend/reports/benchmark_openrouter_nemotron35_supervl_structured_retry_20261107/protocol_manifest.json`
prima di osservare il risultato.

## Matrice completa su due giorni preregistrata il 7 novembre 2026

Per rispettare la quota del modello gratuito viene avviata una nuova matrice
completa 3×2×5, separata da pilot e retry precedenti. La configurazione usa
OpenRouter, `nvidia/nemotron-3.5-super-vl:free`, temperatura `0.1`, reasoning
disabilitato, `schema-json-v2`, limite output 16384, timeout 120 secondi, zero
retry, concorrenza 1, sorgenti `combined` e `research_mode=true`.

I 30 run sono divisi in due blocchi pianificati di 15. Il 7 novembre vengono
eseguiti gli indici 1 e 3 in tutte le sei celle, più l'indice 5 per University
baseline, Library `full_llm` e Hospital baseline. L'8 novembre vengono eseguiti
gli indici 2 e 4 in tutte le celle, più l'indice 5 per University `full_llm`,
Library baseline e Hospital `full_llm`. Ogni giorno contiene cinque run per
dataset; le condizioni sono bilanciate 8/7 e 7/8 nei due giorni.

Il giorno resta una variabile di provenienza e viene considerato nel reporting.
I due blocchi possono formare un'unica sensibilità descrittiva soltanto se
configurazione e revisione software restano immutate. Piano e calendario sono
congelati in
`backend/reports/benchmark_openrouter_nemotron35_supervl_structured_twoday_t01_m16384_20261107/protocol_manifest.json`.
