# Dataset C — Hospital Management

## Struttura

| File | Descrizione |
|---|---|
| `gold_schema.json` | Gold-standard `NormalizedSchema`: 8 tabelle, 7 relazioni |
| `ground_truth.db` | Database SQLite normalizzato (3NF) con i valori di riferimento |
| `source/patients.csv` | Pazienti (100 righe: patient_id, fiscal_code, full_name, birth_date) |
| `source/appointments.csv` | Appuntamenti (200 righe denormalizzate con medico/reparto) |
| `source/operational_notes.txt` | Note operative: mapping dipartimento→reparto, regola fatturazione |
| `source/description.pdf` | Descrizione del dominio (3 pagine) |
| `build_dataset.py` | Generatore riproducibile (seed fisso `20260803`) |

## Contenuto

- **patients** (100), **doctors** (12), **wards** (6), **medications** (10)
- **appointments** (200), **treatments** (250)
- **prescriptions** (300) — junction many-to-many trattamenti↔farmaci
- **invoices** (~160) — fattura riferita all'appuntamento (riferimento ciclico)

## Deviazione documentata dal protocollo (`docs/11`, §1.3)

- Medici e farmaci sono forniti implicitamente nella descrizione/note piuttosto
  che in CSV separati.
- 37 colonne vs le 42 previste dal protocollo (scope iniziale). L'assegnazione
  del reparto è esplicita nel gold-schema ma anche derivabile dal dipartimento
  del medico (entità implicita, esercizio di normalizzazione).

## Uso del valutatore RQ2

```bash
cd backend
python evaluate_population.py \
  --generated-db <db generato>.sqlite \
  --ground-truth ../data/datasets/hospital/ground_truth.db \
  --gold-schema ../data/datasets/hospital/gold_schema.json \
  --output <report>.json
```

Ricostruire gli artefatti:

```bash
python ../data/datasets/hospital/build_dataset.py
```