# Migrazioni del database con Alembic

Il database dell'applicazione (progetti, utenti, lavori, versioni dello schema, cronologia query...) e' descritto
in `backend/app/models/database.py`. Le sue modifiche nel tempo sono migrazioni Alembic in
`backend/alembic/versions/`. I database dei progetti degli utenti (file SQLite generati) non usano Alembic.

## Catena attuale

Una sola catena lineare, un solo `head`:

`c25c5721cbb9` (iniziale) -> `d1a0acl00001` (utenti e condivisione) -> `d2adm00002` (admin e consumi)
-> `d3chat00003` (chat) -> `d4final00004` (schema definitivo) -> `e5jobs00005` (lavori, versioni dello schema,
cronologia query, dialetto di destinazione, OCR).

Il test `backend/tests/test_migrations.py` esegue tutta la catena su un SQLite vuoto fino a `head` e fallisce se
esiste piu' di un head. Va sempre lasciato verde.

## Come funziona `run_migrations`

`run_migrations()` (in `database.py`) viene chiamata all'avvio dell'applicazione e sceglie il percorso in base allo
stato del database:

| Stato | Azione |
|---|---|
| tabella `alembic_version` presente | `upgrade head` |
| esiste `projects` senza `owner_id` (database precedente al ridisegno) | elimina le tabelle nuove create da `create_all`, `stamp c25c5721cbb9`, poi `upgrade head` (i progetti orfani passano all'utente `legacy`) |
| database nuovo (`create_all` ha gia' creato tutto) | `stamp head`, senza eseguire migrazioni |

Per questo ogni migrazione deve essere **idempotente**: su un database gia' versionato, `create_all` puo' aver creato
tabelle nuove ancora vuote prima dell'upgrade. Si controlla con `sa.inspect` se tabella o colonna esistono gia'
(vedi `e5jobs00005`). Se si aggiunge una tabella nuova, va aggiunta anche all'elenco delle tabelle eliminate nel
percorso "database precedente" di `run_migrations`.

## Creare una migrazione

1. Modificare i modelli in `database.py`.
2. Creare il file in `backend/alembic/versions/` con un identificatore breve e `down_revision` uguale all'attuale head
   (si legge con `alembic heads` oppure dal test). Non devono esistere due head.
3. Scrivere `upgrade()` e `downgrade()`. Su SQLite le modifiche a colonne esistenti vanno fatte con
   `op.batch_alter_table(...)`. Per i dati gia' presenti (per esempio la versione 1 dello schema dei progetti
   esistenti) aggiungere un passaggio di riempimento nella stessa migrazione.
4. Provarla su un database vuoto e su una copia di un database reale:

```bash
cd backend
. $HOME/aidb-venv/bin/activate
python -m pytest tests/test_migrations.py -q
```

Con un database da migrare a mano (usa `DATABASE_URL` dell'ambiente, mai credenziali nel repository):

```bash
cd backend
alembic upgrade head                   # applica fino all'ultima
alembic current                       # versione in uso
alembic history --verbose             # catena completa
```

## Applicare una migrazione

In produzione le migrazioni partono da sole all'avvio del servizio (`run_migrations`). Prima di un rilascio che ne
contiene una:

1. fare un `pg_dump` del database (vedi il piano di backup, task 3.2);
2. avviare la nuova immagine: l'upgrade e' eseguito all'avvio; i log riportano la revisione raggiunta;
3. controllare `/ready` e una lettura di un progetto esistente.

## Rollback

- Una revisione indietro: `alembic downgrade -1`; a una revisione precisa: `alembic downgrade d4final00004`.
- Ogni migrazione ha un `downgrade()` che toglie tabelle e colonne aggiunte. Attenzione: il downgrade **cancella i
  dati** delle tabelle e delle colonne rimosse (per esempio le versioni dello schema o la cronologia delle query).
- Il rollback sicuro in produzione e' il ripristino del `pg_dump` fatto prima del rilascio, insieme alla
  reinstallazione dell'immagine precedente. Il downgrade serve soprattutto in sviluppo.
- Una migrazione gia' applicata in produzione non si modifica mai: se contiene un errore si scrive una nuova
  migrazione correttiva.
