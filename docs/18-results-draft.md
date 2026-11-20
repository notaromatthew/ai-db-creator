# Risultati — Bozza RQ1 / RQ2 (DRAFT)

> **Stato:** bozza analitica originariamente costruita dai report del benchmark a due
> temperature di campionamento — **0.1** e **0.5** — 5 run per (dataset,
> condizione), 3 dataset (university / library / hospital). La stima di questo
> documento separa esplicitamente **osservazioni** (dati), **interpretazioni**
> (lettura) e **ipotesi** (da confermare), secondo le regole di governance del
> progetto.
>
> La matrice storicamente descritta come `backend/reports/benchmark/` a
> temperatura 0.1 è stata recuperata dalla
> copia storica e congelata in
> `backend/reports/benchmark_rq1_expert_linked_recovered_20261113/`; il
> collegamento ai 30 schemi RQ1 è verificato direttamente contro gli
> `schema_json` dei progetti e la mappatura seed 42. La serie t=0.5 resta
> riferita a
> `backend/reports/benchmark_t05_full/` (t=0.5), aggregati da
> `backend/aggregate_benchmark.py` → `benchmark_aggregates_01.json` /
> `benchmark_aggregates_05.json`. Gli schemi per RQ1 esperti sono estratti in
> `backend/reports/rq1_expert_package/` da `backend/consolidate_rq1_schemas.py`.
> I risultati RQ1 osservati sono generati da `backend/analyze_rq1_ratings.py`;
> hash, seed e parametri di bootstrap sono congelati in
> `backend/reports/rq1_analysis/manifest.json`.
> La matrice recuperata è primaria per il collegamento RQ1, ma per RQ2 è una
> rivalutazione storica secondaria: non possiede i manifesti originari di
> provider, revisione, `research_mode` e `population_mode`. La matrice RQ2
> strutturata resta documentata con artefatti e limitazioni in
> `docs/21-rq2-primary-results.md`. Non mescolare le due serie; vedere
> `docs/22-rq1-expert-linked-matrix-recovery.md`.
> Il valore 0.1 non è presente nei record originali per-run: deriva dalla
> documentazione e dai default storici e resta quindi un parametro inferito,
> non provenance osservata.

---

## 1. Risultati osservati RQ1 — qualità degli schemi

Il dataset completo contiene 1.350 valutazioni: 45 valutatori × 30 schemi,
senza coppie mancanti o duplicate. Ogni schema appartiene a uno dei tre dataset,
a una delle condizioni `baseline` / `full_llm` e a uno dei cinque run. La scala
effettiva è Likert 1–5. Il piano descriveva tre esperti; il campione osservato è
invece costituito da 45 studenti di informatica di 17–18 anni che stavano
studiando database. Sono pertanto descritti come **trained student raters**, non
come esperti professionali o accademici. La pertinenza della loro formazione non
dimostra da sola indipendenza: modalità individuale, cecità alle condizioni e
assenza di discussione devono risultare dalla documentazione di somministrazione.
Per i minorenni restano da verificare istituzionalmente assenso/consenso e
informativa. La deviazione è documentata, non corretta retrospettivamente.

### Accordo fra valutatori

| Dimensione | Alpha ordinale | IC bootstrap 95% | Interpretazione rispetto alle soglie pianificate |
|---|---:|---:|---|
| D1 — 3NF | 0.812 | 0.742–0.855 | confermativo |
| D2 — naming | -0.018 | -0.021–-0.014 | non interpretabile confermativamente; forte effetto soffitto |
| D3 — vincoli | 0.794 | 0.550–0.855 | stima puntuale tentatively alta, IC ampio |
| D4 — relazioni | 0.803 | 0.564–0.867 | stima puntuale confermativa, IC ampio |
| D5 — dominio | 0.775 | 0.536–0.841 | stima puntuale tentatively alta, IC ampio |
| Complessivo | 0.791 | 0.653–0.846 | tentativo; l'IC scende sotto 0.67 |

D2 ha media 4.956 in entrambe le condizioni e quasi nessuna variabilità. Il suo
alpha vicino a zero è compatibile con il paradosso di prevalenza provocato
dall'effetto soffitto: non dimostra che i dati siano mancanti o incoerenti.

### Confronto fra condizioni

L'unità del confronto primario è lo schema. I 45 giudizi sono aggregati per
ciascuno dei 30 schemi prima dei test, evitando di trattare le 1.350 misure
ripetute come osservazioni indipendenti. I p-value sono corretti con Holm sulle
cinque dimensioni.

| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |
|---|---:|---:|---:|---:|---:|---:|
| D1 — 3NF | 4.364 | 4.871 | +0.507 | 0.221–0.776 | 0.0135 | 1.233 |
| D2 — naming | 4.956 | 4.956 | 0.000 | -0.021–0.022 | 1.0000 | 0.000 |
| D3 — vincoli | 4.622 | 4.944 | +0.321 | 0.116–0.572 | 0.0726 | 0.960 |
| D4 — relazioni | 4.330 | 4.944 | +0.613 | 0.221–1.080 | 0.0726 | 0.959 |
| D5 — dominio | 4.618 | 4.938 | +0.320 | 0.117–0.564 | 0.0726 | 0.975 |

Solo D1 supera la soglia 0.05 dopo correzione Holm. D3–D5 mostrano differenze
descrittive ed effetti standardizzati grandi, ma non sono dichiarate
significative nel confronto molteplice primario. L'analisi appaiata per
dataset/run è conservata come sensibilità separata.

### Pannello separato con tre esperti del settore

La seconda raccolta, mantenuta separata e non pooled con i 45 studenti,
comprende 90 righe: tre esperti del settore × 30 schemi × cinque dimensioni. La
numerosità pianificata è quindi raggiunta. Per i primi due esperti, compilazione
individuale senza confronto o accesso ai punteggi reciproci e cecità alle
etichette di condizione sono state attestate dall'utente il 14 novembre 2026.
Il terzo valutatore è stato identificato dall'utente come esperto il 18 novembre;
la sua indipendenza è stata confermata dall'utente il 19 novembre 2026. La
cecità del terzo esperto alle condizioni non è invece documentata e resta una
limitazione procedurale esplicita.

L'accordo esatto è 20/150 celle e 0/30 vettori-schema; quello adiacente
complessivo è 63,3%. L'alpha ordinale complessivo è 0,054 (IC bootstrap 95%
-0,241–0,300): il pannello non mostra un consenso forte. Per dimensione, alpha
è 0,242 per D1, -0,463 per D2 e 0,103 per D3–D5. La forte divergenza del terzo
profilo rispetto ai primi due viene conservata come risultato osservato e non
corretta o esclusa retrospettivamente.

| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |
|---|---:|---:|---:|---:|---:|---:|
| D1 — 3NF | 3,644 | 4,444 | +0,800 | 0,422–1,156 | 0,0021 | 1,515 |
| D2 — naming | 4,444 | 4,533 | +0,089 | -0,044–0,200 | 0,2073 | 0,472 |
| D3 — vincoli | 4,000 | 4,533 | +0,533 | 0,178–0,911 | 0,0670 | 0,974 |
| D4 — relazioni | 4,000 | 4,533 | +0,533 | 0,178–0,911 | 0,0670 | 0,974 |
| D5 — dominio | 4,000 | 4,533 | +0,533 | 0,178–0,912 | 0,0670 | 0,974 |

L'unità analitica è lo schema (15 per condizione). Input pseudonimizzato, hash
della sorgente originale e canonica, descrittive e risultati completi sono in
`backend/reports/rq1_expert_replication/` e sono rigenerati da
`backend/analyze_rq1_expert_replication.py`.

---

## 2. Osservazioni consolidate (RQ2 — accuratezza di popolamento a livello di cella)

La matrice collegata agli schemi RQ1 è stata recuperata e rivalutata offline,
ma resta una sensibilità storica secondaria per RQ2. La classificazione non è
una scelta prestazionale: deriva dall'assenza dei manifesti originari per-run.
Risultati, hash e limitazioni sono in
`docs/22-rq1-expert-linked-matrix-recovery.md`.

### Matrice verificata `schema-json-v2` — 7–8 novembre 2026

La nuova matrice completa contiene 30/30 run riusciti, cinque per ciascuna
coppia dataset/condizione, zero fallback e una sola revisione software. È stata
eseguita in due blocchi preregistrati di 15 run con OpenRouter,
`nvidia/nemotron-3.5-super-vl:free`, temperatura `0.1`, sorgenti `combined` e
contratto `schema-json-v2`. Tutti i 195 hash artefatto, 100 hash sorgente e 30
hash delle specifiche di valutazione sono stati ricalcolati senza discrepanze.

| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali |
|---|---|---:|---:|---:|---:|---:|
| University | baseline | 5 | 0.9983 | 0.9402 | 0.9638 | 0.4400 |
| University | full_llm | 5 | 0.6667 | 0.6636 | 0.6651 | 0.3600 |
| Library | baseline | 5 | 0.9500 | 0.9213 | 0.9348 | 0.6200 |
| Library | full_llm | 5 | 1.0000 | 0.9713 | 0.9848 | 0.4000 |
| Hospital | baseline | 5 | 0.9996 | 0.9312 | 0.9496 | 0.4200 |
| Hospital | full_llm | 5 | 0.6496 | 0.6364 | 0.6427 | 0.2000 |

Il successo tecnico è completo, ma l'equivalenza funzionale resta parziale.
Inoltre il giorno 2 presenta F1 inferiore in quattro celle su sei; con 2–3 run
per giorno/cella è un segnale descrittivo di possibile deriva del provider, non
una stima causale. La matrice usa sorgenti congiunte e non consente ancora il
confronto causale fra formati. La fixture equivalente CSV/XLSX/TXT/PDF è stata
ora congelata e validata, ma la matrice separata da 40 run non è stata ancora
eseguita. L'adjudication cieca delle 1.294 discrepanze è stata completata da due
revisori indipendenti, seguita dal consenso sui 327 disaccordi. Il ledger finale
contiene 967 errori, 4 equivalenze funzionali, 12 casi ambigui nel gold standard
e 311 casi non determinabili dagli artefatti ciechi. Risultati e manifesti sono
in `backend/reports/rq2_adjudication_completed/` e
`backend/reports/rq2_final_analysis/`.

### Serie storica non verificata — non usare per le conclusioni

Condizioni: **baseline** = schema gold applicato deterministicamente + popolamento
LLM; **full_llm** = schema generato dall'LLM + popolamento LLM. Metrica: F1
cella-cella (macro) dopo allineamento colonne (protocollo §6, §9.3).

### Tabella 1 — F1 aggregato a temperature 0.1 e 0.5

| Dataset | Condizione | F1 @0.1 | F1 @0.5 | range per-run @0.5 | Prec @0.5 | Rec @0.5 |
|---|---|---|---|---|---|---|
| university | baseline | 0.693 | **0.766** | 0.766 (cost.) | 0.771 | 0.814 |
| university | full_llm | 0.302 | **0.351** | 0.233–0.446 | 0.606 | 0.442 |
| library | baseline | 0.733 | **0.733** | 0.733 (cost.) | 0.700 | 0.800 |
| library | full_llm | 0.733 | **0.737** | 0.733–0.742 | 0.700 | 0.800 |
| hospital | baseline | 0.721 | **0.670** | 0.415–0.787 | 0.745 | 0.772 |
| hospital | full_llm | 0.620 | **0.688** | 0.606–0.752 | 0.810 | 0.603 |

Osservazioni puntuali:

- **library** è la condizione più stabile: F1 ≈ 0.733–0.737 sia a 0.1 che a 0.5,
  con range per-run quasi piatto (0.733–0.742). F1, precision e recall sono
  quasi identici → piccolo dataset, poca varianza campionabile.
- **university full_llm** è il caso peggiore in assoluto (F1 ≈ 0.30–0.35), molto
  sotto la baseline (0.69–0.77). A 0.5 compare varianza **reale** (0.233–0.446):
  il modello può produrre schemi/popolamenti sensibilmente migliori o peggiori
  a seconda del run.
- **hospital full_llm**: a 0.5 il mean sale (0.620 → 0.688) e la varianza è
  evidente (0.606–0.752). La **precision** del full_llm resta alta (~0.81,
  superiore alla baseline 0.745) ma il recall è molto più basso (~0.60): il
  full_llm "inserisce meno" ma manca più righe.
- **university baseline** a 0.5 è stabile e alto (0.766, range costante): a 0.1
  il run1 anomalo (0.403) era il punto fuori distribuzione che trainava la media
  giù; a 0.5 i 5 run convergono allo stesso 0.766.
- **hospital baseline** a 0.5 ha varianza ampia (0.415–0.787) nonostante lo
  schema gold deterministico → il peso della varianza a livello di *popolazione*
  è considerevole anche in baseline.

### Tabella 2 — Giudice supplementare (LLM-as-judge, temperature 0.0)

Valori riportati per la run a **t=0.5** (le parentesi indicano il valore a t=0.1
dove differisce).

| Dataset | Condizione | eq schema | value-acc | completeness | n |
|---|---|---|---|---|---|
| university | baseline | 100.0 | 66.0 (68.0) | 73.0 (58.4) | 5 |
| university | full_llm | 86.0 (93.8) | **60.0** (53.8) | 70.6 (73.0) | 5 |
| library | baseline | 100.0 | **12.0** (10.0) | 50.0 (60.0) | 5 |
| library | full_llm | 94.0 (95.0) | 30.0 (28.0) | 44.0 (40.0) | 5 |
| hospital | baseline | 100.0 | 25.0 (29.0) | 52.0 (61.0) | 5 |
| hospital | full_llm | 87.0 (87.0) | 50.0 (42.0) | 68.0 (56.0) | 5 |

Osservazioni: l'equivalenza di **schema** è alta ovunque (≥86), mentre la
**value-accuracy** è molto più bassa (12–66). Questo è il segnale chiave già
verificato manualmente: l'F1 deterministico può restare alto (0.73) anche quando
i *valori* sono sistematicamente diversi, perché l'F1 allinea i PK ma non valuta
la correttezza semantica dei valori. Il giudice è stabile a 0.0: la differenza
rispetto al 0.1 riflette schemi/popolamenti realmente diversi, non il giudice.

---

## 3. Success criteria (protocollo § / roadmap Fase 4) — confronto

| Criterio | Target | Risultato osservato | Esito |
|---|---|---|---|
| F1 cell-level su sorgenti CSV/Excel | ≥ 0.85 | 0.30–0.77 (t=0.5) | ✗ NON RAGGIUNTO |
| F1 cell-level su PDF/TXT | ≥ 0.60 | non misurato separatamente | ? |
| Duplicate rate (PK duplicate) | < 5% | 0.0 in tutti i 6 gruppi | ✓ (banale, vedi nota) |
| Precision ≥ Recall (no over-inserimento) | P ≥ R | true su tutti i 6 gruppi | ✓ |

**Osservazione di governance:** nessun gruppo raggiunge la soglia F1 0.85 in
questa configurazione (modelle corrente, temperature 0.1 e 0.5). Questo NON è
necessariamente un fallimento del sistema: lo studio deve decidere quanto era
'attesa' la soglia con default deterministici a bassa temperatura, e se servono
temperatura più alta o un modello diverso prima di dichiarare esito finale.

**Nota metodologica su duplicate rate:** il tasso è 0.0 perché il vincolo PRIMARY
KEY imposto dal DB generato impedisce chiavi duplicate per costruzione (verifica
su entrambe le temperature). Il criterio "<5%" è quindi banalmente soddisfatto
per costruzione, non per merito della pipeline di popolamento. Per una metrica
informativa sui duplicati servirebbe una definizione di "duplicato" diversa dalle
PK (es. righe identiche su tutte le colonne non-PK), non prevista dal protocollo.

---

## 4. Interpretazioni (lettura non confermata)

1. **Varianza reale a t=0.5, piatta a t=0.1.** I range per-run a 0.5 (es.
   university full_llm 0.233–0.446; hospital baseline 0.415–0.787) mostrano che
   a temperatura 0.5 il run campiona davvero la distribuzione del modello,
   mentre a 0.1 l'output è quasi deterministico (range piatti, es. library
   identica ×5). La media/σ su run a 0.1 NON misura la distribuzione; a 0.5 sì.
   **Implicazione per lo studio:** la temperatura di riferimento per l'inferenza
   va scelta e dichiarata; non è indipendente dai risultati.
2. Il pattern "F1 alto ma value-accuracy bassa" in **library baseline** (F1 0.73,
   giudice value-acc 12/100) è compatibile con un'**ipotesi di mismatch di
   chiave/valore**: i PK si allineano (F1 "vede" i match di riga) ma i valori
   sono sistematicamente diversi. L'F1 macro su PK **sovrastima** la correttezza
   semantica: per questo il giudice è riportato come segnale complementare e non
   sostitutivo.
3. In **hospital** il full_llm "inserisce meno" (precision alta ~0.81, recall
   basso ~0.60) suggerisce un comportamento **conservatore**: il modello genera
   poche righe ma più affidabili quando le genera. Ipotesi da verificare sulle
   righe mancanti specifiche.
4. **university full_llm** è il collo di bottiglia, ma la varianza a 0.5
   (0.233–0.446) indica che il problema non è deterministico: alcuni run
   raggiungono F1 ~0.45, altri collassano. Se questo dipende dal run (campione
   di righe) o dallo schema generato (struttura) è da investigare con l'analisi
   per-tabella dei run migliori/peggiori.

---

## 5. Ipotesi da confermare prima di scrivere i risultati finali

- [x] **Varianza**: rieseguito il set completo a t=0.5 → varianza reale per-run
      dove conta (university/hospital full_llm); CI ancora larghi (n=5) ma
      informativi sull'effetto temperatura.
- [x] **Duplicate rate**: estratto (0.0 in tutti i gruppi per costruzione PK).
- [ ] **Soglia F1**: decidere il criterio finale (0.85 su CSV era una soglia di
      progetto riportata nella roadmap Fase 4). Confermare con sorgenti
      separate CSV vs PDF/TXT.
- [ ] **Run1 baseline university a t=0.1** (F1 0.403 vs 0.766 degli altri 4):
      ispezionare se è un outlier genuino o un artefatto; a t=0.5 i 5 run
      convergono tutti a 0.766.
- [ ] **Carattere del campione**: n=5 per cella è comunque limitato per
      inferenza confermativa; decidere se aumentare i run (con rate limit 15/min
      il costo è ~5 min per run per dataset).
- [ ] Adjudication: a t=0.5 tutti i 30 run hanno scores (n=5 omogeneo) — a t=0.1
      university/full_llm aveva n=4 per un run in errore; se si riportano
      entrambe le temperature, dichiarare la differenza.
- [ ] **Scelta temperatura di riferimento**: decidere se lo studio usa t=0.1
      (riproducibilità) o t=0.5 (distribuzione reale) come configurazione
      primaria; impatta il confronto con la baseline e le soglie.
- [ ] **Analisi per-tabella** dei run migliori/peggiori di university full_llm a
      t=0.5 per attribuire il collasso a schema vs popolamento.

---

## 6. Struttura suggerita per lo studio (mappa al paper/tesi)

1. **RQ1** dispone di 1.350 valutazioni complete su 30 schemi. Analisi,
   pseudonimizzazione, accordo, descrittive e confronti sono riproducibili in
   `backend/reports/rq1_analysis/`. Resta umana la verifica documentale dei
   criteri di idoneità dei 45 valutatori.
2. **RQ2** dispone della matrice strutturata completa descritta in `docs/21` e
   della rivalutazione storica secondaria collegata a RQ1 descritta in
   `docs/22`. I 30 database, i record grezzi recuperati, i ledger e gli hash
   della rivalutazione sono ora presenti. Sono pronti anche i due fogli ciechi
   per l'adjudication e la fixture semanticamente equivalente in quattro
   formati. Le due revisioni umane e il consenso sono conclusi. Anche la
   matrice separata per formato è conclusa: 40 run Gemini congelati, 38
   successi senza fallback e due fallimenti di generazione conservati.
3. I numeri RQ2 vanno messi in relazione CRITICA con l'adjudication: F1 e giudice
   non sempre concordano → nel paper va dichiarato che l'F1 deterministico è un
   limite quando i PK differiscono.

---

## 7. Artefatti generati in questa sessione

| File | Ruolo |
|---|---|
| `backend/consolidate_rq1_schemas.py` | Estrarre 30 schemi da `app.db`, render come printout anonimizzati, pacchetto §8 |
| `backend/reports/rq1_expert_package/` | `schemas/S*.md`, `mapping.csv`, `ratings_template.csv`, `README.md` |
| `backend/analyze_rq1_ratings.py` | Validazione, pseudonimizzazione e analisi riproducibile delle valutazioni RQ1 |
| `backend/analyze_rq1_expert_replication.py` | Pannello RQ1 separato: canonicalizzazione pseudonima, accordo a tre esperti e confronto schema-level |
| `backend/reports/rq1_expert_replication/` | Input canonico pseudonimizzato, manifesti/hash e risultati del pannello a tre esperti |
| `backend/reports/rq1_analysis/` | Manifesto, matrice pseudonimizzata, descrittive, accordo, confronti e report |
| `backend/aggregate_benchmark.py` | Aggregazione numeri RQ2 (F1/CI/adjudication/duplicate rate) da report → JSON |
| `backend/reports/benchmark_rq1_expert_linked_recovered_20261113/` | Matrice storica RQ1 recuperata, 30 database, rivalutazione RQ2 secondaria e manifesti |
| `backend/reports/benchmark_format_equivalence_google_gemini35flashlite_20261120/` | Matrice RQ2 per formato congelata: 40 run, manifesti e artefatti grezzi |
| `backend/analyze_rq2_format_matrix.py` / `backend/reports/rq2_format_analysis/` | Validazione e analisi esplorativa riproducibile del confronto CSV/XLSX/TXT/PDF |
| `backend/analyze_rq2_format_recovered_sensitivity.py` / `backend/reports/rq2_format_post_recovery_sensitivity/` | Overlay secondario post-recovery 40/40, senza sostituire il risultato primario 38/40 |
| `backend/build_research_evidence_index.py` / `backend/reports/research_evidence_index/` | Indice finale pubblico RQ1/RQ2: classificazione, hash e controlli privacy degli artefatti conclusi |
| `backend/recover_expert_linked_matrix.py` | Recupero riproducibile, verifica linkage seed 42, sanitizzazione e rivalutazione offline |
| `backend/reports/benchmark_aggregates_01.json` / `_05.json` | Aggregati storici originali non recuperati; non necessari per la rivalutazione corrente |
| `backend/reports/benchmark_t05_full/` | Serie t=0.5 ancora assente; non mescolare con la matrice recuperata |
| `backend/analyze_user_study.py` | Pipeline predisposta per RQ0/RQ3/RQ4; resta inattiva finché non esistono export osservati completi |
