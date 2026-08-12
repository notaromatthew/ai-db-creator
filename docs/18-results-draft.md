# Risultati — Bozza RQ1 / RQ2 (DRAFT)

> **LEGACY EXPLORATORY / NON-CONFIRMATORY.** Questi risultati sono stati prodotti con la semantica precedente del valutatore e non devono essere presentati come risposta confermativa a RQ1/RQ2. Il classificatore, i denominatori di righe mancanti/extra, l'allineamento e gli intervalli d'incertezza sono stati successivamente sottoposti a revisione metodologica. Tutti i benchmark destinati al paper devono essere rigenerati con evaluator, allineamenti, workload, modello e temperatura congelati. I numeri legacy non sono direttamente combinabili con quelli del nuovo protocollo.

> **Stato:** bozza analitica costruita dai report reali del benchmark a due
> temperature di campionamento — **0.1** e **0.5** — 5 run per (dataset,
> condizione), 3 dataset (university / library / hospital). La stima di questo
> documento separa esplicitamente **osservazioni** (dati), **interpretazioni**
> (lettura) e **ipotesi** (da confermare), secondo le regole di governance del
> progetto.
>
> Fonte dei numeri: `backend/reports/benchmark/` (t=0.1) e
> `backend/reports/benchmark_t05_full/` (t=0.5), aggregati da
> `backend/aggregate_benchmark.py` → `benchmark_aggregates_01.json` /
> `benchmark_aggregates_05.json`. Gli schemi per RQ1 esperti sono estratti in
> `backend/reports/rq1_expert_package/` da `backend/consolidate_rq1_schemas.py`.

---

## 1. Osservazioni consolidate legacy (RQ2 — sviluppo esplorativo)

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

## 2. Success criteria (protocollo § / roadmap Fase 4) — confronto

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

## 3. Interpretazioni (lettura non confermata)

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

## 4. Ipotesi da confermare prima di scrivere i risultati finali

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

## 5. Struttura suggerita per lo studio (mappa al paper/tesi)

1. **RQ1** usa il pacchetto `rq1_expert_package/` (30 schemi anonimizzati) →
   valutazione 3 esperti → alpha di Krippendorff + confronto per arma. Finora
   non è ancora eseguita (serve recruiting + scoring umano).
2. **RQ2** è già automatizzata (numeri sopra). Resta da chiudere: soglia,
   sorgenti separate, scelta temperatura di riferimento.
3. I numeri RQ2 vanno messi in relazione CRITICA con l'adjudication: F1 e giudice
   non sempre concordano → nel paper va dichiarato che l'F1 deterministico è un
   limite quando i PK differiscono.

---

## 6. Artefatti generati in questa sessione

| File | Ruolo |
|---|---|
| `backend/consolidate_rq1_schemas.py` | Estrarre 30 schemi da `app.db`, render come printout anonimizzati, pacchetto §8 |
| `backend/reports/rq1_expert_package/` | `schemas/S*.md`, `mapping.csv`, `ratings_template.csv`, `README.md` |
| `backend/aggregate_benchmark.py` | Aggregazione numeri RQ2 (F1/CI/adjudication/duplicate rate) da report → JSON |
| `backend/reports/benchmark_aggregates_01.json` / `_05.json` | Numeri consolidati per t=0.1 e t=0.5 |
| `backend/reports/benchmark_t05_full/` | Report del benchmark completo a t=0.5 (30 run, --adjudicate) |
