# Risultati — Bozza RQ1 / RQ2 (DRAFT)

> **Stato:** bozza analitica costruita dai report reali del benchmark a
> **temperature 0.1**, 5 run per (dataset, condizione), 3 dataset
> (university / library / hospital). La stima di questo documento separa
> esplicitamente **osservazioni** (dati), **interpretazioni** (lettura) e
> **ipotesi** (da confermare), secondo le regole di governance del progetto.
>
> Fonte dei numeri: `backend/reports/benchmark/` (run<NN>.json +
> *_summary.json), aggregati da `backend/aggregate_benchmark.py` →
> `backend/reports/benchmark_aggregates.json`. Gli schemi per RQ1 esperti sono
> estratti in `backend/reports/rq1_expert_package/` da
> `backend/consolidate_rq1_schemas.py`.

---

## 1. Osservazioni consolidate (RQ2 — accuratezza di popolamento a livello di cella)

Condizioni: **baseline** = schema gold applicato deterministicamente + popolamento
LLM; **full_llm** = schema generato dall'LLM + popolamento LLM. Metrica: F1
cella-cella (macro) dopo allineamento colonne (protocollo §6, §9.3).

### Tabella 1 — F1 per-run e aggregato

| Dataset | Condizione | F1 mean | F1 (min–max) | Prec | Rec | missing/run | extra/run |
|---|---|---|---|---|---|---|---|
| university | baseline | **0.693** | 0.403–0.766 | 0.678 | 0.768 | 42.6 | 25.6 |
| university | full_llm | **0.302** | 0.298–0.314 | 0.341 | 0.337 | 56.2 | 36.6 |
| library | baseline | **0.733** | 0.733 (cost.) | 0.700 | 0.800 | 24.0 | 0.0 |
| library | full_llm | **0.733** | 0.733 (cost.) | 0.700 | 0.800 | 24.0 | 0.0 |
| hospital | baseline | **0.721** | 0.543–0.789 | 0.741 | 0.808 | 335.2 | 29.6 |
| hospital | full_llm | **0.620** | 0.522–0.748 | 0.816 | 0.578 | 495.0 | 16.8 |

Osservazioni puntuali:

- **library** è la condizione più stabile: praticamente lo stesso F1 (0.733) a
  prescindere da baseline vs full_llm e da run a run. F1, precision e recall
  sono identici nei 5 run → a temperature 0.1 il modello produce output
  quasi deterministici.
- **university full_llm** è il caso peggiore in assoluto (F1 ≈ 0.30), molto
  sotto la baseline (0.69): il divario è guidato da un numero elevato di righe
  mancanti (56.2) ed extra (36.6) per run.
- **hospital** mostra il divario PIÙ piccolo tra arm e una **precision** del
  full_llm (0.816) superiore alla baseline (0.741), ma recall molto più basso
  (0.578 vs 0.808): il full_llm "inserisce meno" ma manca più righe.
- In **hospital full_llm** ci sono ~495 righe mancanti/run contro 335 della
  baseline: entrambe alte, ma il full_llm ad alto divario.

### Tabella 2 — Giudice supplementare (LLM-as-judge, temperature 0.0)

| Dataset | Condizione | eq schema | value-acc | completeness | n |
|---|---|---|---|---|---|
| university | baseline | 100.0 | 68.0 | 58.4 | 5 |
| university | full_llm | 93.8 | 53.8 | 73.0 | 4 |
| library | baseline | 100.0 | **10.0** | 60.0 | 5 |
| library | full_llm | 95.0 | 28.0 | 40.0 | 5 |
| hospital | baseline | 100.0 | 29.0 | 61.0 | 5 |
| hospital | full_llm | 87.0 | 42.0 | 56.0 | 5 |

Osservazioni: l'equivalenza di **schema** è alta ovunque (≥87), mentre la
**value-accuracy** è molto più bassa (10–68). Questo è il segnale chiave già
verificato manualmente: l'F1 deterministico può restare alto (0.73) anche quando
i *valori* sono sistematicamente diversi, perché l'F1 sa coniugare i PK
allineandoli ma non valuta la correttezza semantica dei valori.

---

## 2. Success criteria (protocollo § / roadmap Fase 4) — confronto

| Criterio | Target | Risultato osservato | Esito |
|---|---|---|---|
| F1 cell-level su sorgenti CSV/Excel | ≥ 0.85 | 0.30–0.73 | ✗ NON RAGGIUNTO |
| F1 cell-level su PDF/TXT | ≥ 0.60 | non misurato separatamente | ? |
| Duplicate rate | < 5% | non estratto dagli aggregati | ? |
| Precision ≥ Recall (no over-inserimento) | P ≥ R | true su tutti i 6 gruppi | ✓ |

**Osservazione di governance:** nessun gruppo raggiunge la soglia F1 0.85 in
questa configurazione (temperature 0.1, modello corrente). Questo NON è
necessariamente un fallimento del sistema: lo studio deve decidere quanto era
'attesa' la soglia con default deterministici a bassa temperatura, e se servono
run a temperatura più alta o un modello diverso prima di dichiarare esito finale.

---

## 3. Interpretazioni (lettura non confermata)

1. La bassa varianza per-run (soprattutto library, identica ×5) è coerente con
   **temperature 0.1**: l'output LLM è pressoché deterministico. Quindi la
   media/σ su run NON misura la distribuzione del modello: misura quasi solo la
   ripetizione dello stesso output. **Implica:** per stimare la variabilità reale
   serve una run a temperatura più alta (es. 0.7), già realizzata come sperimento
   isolato (univfix) ma non come set completo.
2. Il pattern "F1 alto ma value-accuracy bassa" in **library baseline** è
   compatibile con un'**ipotesi di mismatch di chiave/valore**: i PK si allineano
   (quindi F1 "vede" i match di riga), ma i valori contenuti sono diversi
   (giudice 10/100). L'F1 macro su PK **sovrastima** la correttezza semantica.
3. In **hospital** il full_llm che "inserisce meno" (missing alti, prec alta)
   suggerisce un comportamento di **conservatore**: il modello genera poche righe
   ma più affidabili quando le genera. Ipotesi da verificare sulle righe mancanti
   specifiche.
4. **university full_llm** è il collo di bottiglia. la baseline stessa ha un
   singolo run basso (0.403) — anomalia da rivedere nel run01 di university
   baseline prima di interpretare la media.

---

## 4. Ipotesi da confermare prima di scrivere i risultati finali

- [ ] **Varianza**: rieseguire il set completo a temperature più alta (0.5–0.7)
      e confrontare CI. Attualmente i CI sono larghissimi (es. university
      full_llm CI 0.07–0.70) e non informativi.
- [ ] **Soglia F1**: decidere il criterio finale (0.85 su CSV era una soglia di
      progetto riportata nella roadmap Fase 4). Confermare con sorgenti
      separate CSV vs PDF/TXT.
- [ ] **Duplicate rate**: estrarre la metrica di qualità (duplicati) dagli
      output per completare i success criteria.
- [ ] **Anomalia run01 baseline university** (F1 0.403 vs 0.766 degli altri 4):
      ispezionare prima di includerlo nella media.
- [ ] **Carattere del campione**: 5 run a temperature 0.1 sono insufficienti per
      inferenza; per RQ2 confermativa serve ripetizione adeguata sul
      comportamento del modello.
- [ ] Adjudication: n=4 in university full_llm (1 run in errore) — decidere se
      ripetere il run4 per rendere il conteggio omogeneo.

---

## 5. Struttura suggerita per lo studio (mappa al paper/tesi)

1. **RQ1** usa il pacchetto `rq1_expert_package/` (30 schemi anonimizzati) →
   valutazione 3 esperti → alpha di Krippendorff + confronto per arma. Finora
   non è ancora eseguita (serve recruiting + scoring umano).
2. **RQ2** è già automatizzata (numeri sopra). Resta da chiudere: soglia,
   duplicate rate, sorgenti separate, varianza.
3. I numeri RQ2 vanno messi in relazione CRITICA con l'adjudication: F1 e giudice
   non sempre concordano → nel paper va dichiarato che l'F1 deterministico è un
   limite quando i PK differiscono.

---

## 6. Artefatti generati in questa sessione

| File | Ruolo |
|---|---|
| `backend/consolidate_rq1_schemas.py` | Estrarre 30 schemi da `app.db`, render come printout anonimizzati, pacchetto §8 |
| `backend/reports/rq1_expert_package/` | `schemas/S*.md`, `mapping.csv`, `ratings_template.csv`, `README.md` |
| `backend/aggregate_benchmark.py` | Aggregazione numeri RQ2 da report → JSON |
| `backend/reports/benchmark_aggregates.json` | Numeri consolidati usati in questo documento |