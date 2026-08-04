# Dataset A — University Enrollment

## Struttura

| File | Descrizione |
|---|---|
| `gold_schema.json` | Gold-standard `NormalizedSchema`: 3 tabelle, 9 colonne, 2 FK |
| `ground_truth.db` | Database SQLite normalizzato (3NF) con i valori di riferimento |
| `source/enrollments.csv` | CSV **denormalizzato** (30 righe) come verrebbe caricato dall'utente |
| `source/description.pdf` | Descrizione del dominio in due paragrafi |
| `build_dataset.py` | Generatore riproducibile (seed fisso `20260803`) |

## Contenuto

- **students** (30): `student_id`, `name`, `email`
- **courses** (8): `course_id`, `course_code`, `title`, `credits`
- **enrollments** (45): `student_id`+`course_id` (PK composita), `semester`, `grade`

## Deviazione documentata dal protocollo (`docs/11`, §1.1)

Il protocollo prevede un CSV a **3 colonne**; questa prima versione usa un CSV
**denormalizzato a 7 colonne** (nome/email studente + codice/titolo/crediti corso +
semestre/voto) per rendere non ambigua la ricostruzione delle 3 tabelle a partire
dal solo CSV. Se serve fedeltà stretta al protocollo, ridurre a 3 colonne prima
delle run comparative.

## Uso del valutatore RQ2

```bash
cd backend
python evaluate_population.py \
  --generated-db <db generato>.sqlite \
  --ground-truth ../data/datasets/university/ground_truth.db \
  --gold-schema ../data/datasets/university/gold_schema.json \
  --output <report>.json
```

Ricostruire gli artefatti:

```bash
python ../data/datasets/university/build_dataset.py
```