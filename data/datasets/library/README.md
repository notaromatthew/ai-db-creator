# Dataset B — Library Management

## Struttura

| File | Descrizione |
|---|---|
| `gold_schema.json` | Gold-standard `NormalizedSchema`: 5 tabelle, 4 FK |
| `ground_truth.db` | Database SQLite normalizzato (3NF) con i valori di riferimento |
| `source/members.csv` | Iscritti (20 righe: member_id, full_name, email, joined_on) |
| `source/books.csv` | Libri (50 righe: book_id, isbn, title, author, category_name) |
| `source/loans_members.csv` | Prestiti denormalizzati con dati membro (one-to-many) |
| `source/description.pdf` | Descrizione del dominio (1 pagina) |
| `build_dataset.py` | Generatore riproducibile (seed fisso `20260803`) |

## Contenuto

- **categories** (10): `category_id`, `name`
- **members** (20): `member_id`, `full_name`, `email`, `joined_on`
- **books** (50): `book_id`, `isbn`, `title`, `author`, `category_id`
- **loans** (60): `loan_id`, `book_id`, `member_id`, `loan_date`, `due_date`
- **fines** (variabile, ~60% dei prestiti): `fine_id`, `loan_id`, `amount`, `paid_on`

## Deviazione documentata dal protocollo (`docs/11`, §1.2)

- Il protocollo descrive prestiti e multe derivabili dal ritardo; qui prestiti e
  multe sono generati a tempo di record per popolare la ground-truth. Un CSV
  denormalizzato `loans_members.csv` esercita la ricostruzione one-to-many.
- `category_name` nella CSV dei libri è denormalizzato (il gold-schema usa
  `category_id`), per testare la risoluzione semantica.

## Uso del valutatore RQ2

```bash
cd backend
python evaluate_population.py \
  --generated-db <db generato>.sqlite \
  --ground-truth ../data/datasets/library/ground_truth.db \
  --gold-schema ../data/datasets/library/gold_schema.json \
  --output <report>.json
```

Ricostruire gli artefatti:

```bash
python ../data/datasets/library/build_dataset.py
```