# User Manual

## Introduction

AI-DB-Creator lets you create a fully normalised relational database by simply describing what you need and uploading your documents. The system uses an AI assistant to design the database structure, populate it with your data, and let you explore everything through a visual interface.

This guide walks through the complete workflow in 10 steps.

---

## Step 1: Create a Project

1. Open the application in your browser (default: `http://localhost:5173`).
2. On the Dashboard, enter a **Project name** (e.g., "University Database").
3. Optionally, enter a **description** of what you want to model (e.g., "A database for a university with students, courses, professors, and enrollments").
4. Click **Create Project**.

You will be taken to the project workspace, which has three tabs: **Schema**, **Data**, and **Query**.

The **Guided Workflow** bar at the top shows your progress through four steps: Upload documents → Generate schema → Populate data → Explore.

---

## Step 2: Upload Documents

Click the upload area at the top of the project page and select one or more files. Supported formats:

| Format | Extension | Notes |
|---|---|---|
| Comma-Separated Values | `.csv` | Auto-detects encoding (UTF-8, Latin-1, Windows-1252) and delimiter (comma, semicolon, tab, pipe) |
| Excel | `.xlsx`, `.xls` | All sheets are read; each sheet is treated as a data source |
| PDF | `.pdf` | Text content is extracted; images and scanned documents are not processed |
| Plain Text | `.txt` | UTF-8 encoded |
| SQL Dump | `.sql` | Imported as a database (schema + data) |

Uploaded files appear in the document list below the upload area. You can delete them using the × button.

---

## Step 3: Generate Schema

There are two ways to generate the database schema:

### Option A: Quick Generate

1. Click the **Quick Generate** section to expand it.
2. Type a description of your database (e.g., "A system to track inventory, suppliers, and purchase orders").
3. Click **Generate**.

The system sends your description plus the text extracted from all uploaded documents to the AI, which returns a full database schema.

### Option B: Chat Interface

1. Use the chat box to describe your requirements conversationally.
2. The AI responds with a proposed schema and an explanation.
3. You can continue the conversation: ask for changes ("Add a phone number column to the customers table", "Split the addresses into a separate table").
4. When satisfied, click **Accept** to save the schema.

The generated schema shows each table as a card listing its columns, data types, and constraints (PK = primary key, FK = foreign key, NN = not null).

---

## Step 4: Review and Edit the Schema

Before creating the database, you can review and modify the schema.

### Switch to Edit Mode
1. Click the **Modifica** (Edit) button at the top of the schema section.
2. The schema becomes editable.

### What You Can Edit
- **Table names** — click the table name field to rename.
- **Add/remove tables** — use the **+ Aggiungi tabella** button or **Elimina tabella** on each table.
- **Column names and types** — direct text input.
- **Constraints** — checkboxes for Primary Key (PK), Foreign Key (FK), and Not Null (NN).
- **Add/remove columns** — use **+ Aggiungi colonna** or the × per column.

### Relationships
The relationships between tables are shown below the table cards (e.g., `clienti.id ──N──→ scontrini.cliente_id`). These are read-only in the current version.

### Save or Cancel
- Click **Salva** to save your edits. The database is created or updated.
- Click **Annulla** to discard changes.

---

## Step 5: Populate Tables with Data

Once the schema is approved and saved:

1. Click the **Populate Tables** button.
2. The complete content of every uploaded document (CSV, Excel, PDF, TXT) is sent to the AI, which decides how to map the values into the approved schema. The AI is the primary population route for every document type and overrides any deterministic matching. Only duplicate rows that are already present in the target tables are discarded; NULL/empty values are accepted and inserted where allowed by the schema.
3. If the AI returns no usable SQL, the system falls back to deterministic header matching as a recovery path.
4. A green message shows how many rows were inserted per table and the extraction method (e.g., `clienti: +15 · llm`).
5. If some rows could not be inserted (e.g., because of missing foreign key references), they are reported as skipped.

The population process is **idempotent** — you can run it multiple times and existing data will not be duplicated (uses `INSERT OR IGNORE`).

### Provenance and confidence

Population metadata records the source document, sheet/table, source row/header/column, target table/column, and mapping method without copying raw cell values into research logs. When the interface says **confidence not calibrated**, it means no validated probability of correctness is available; review the mapped data rather than treating the label as a quality guarantee.

---

## Step 6: Explore Data

Switch to the **Data** tab to browse and manipulate your populated tables.

### Viewing Data
- Each table is displayed in its own section with a scrollable table grid.
- Column headers show the data type.
- Row counts are shown (e.g., "15/15 righe").

### Searching and Filtering
- **Global search** — type in the search box to filter rows across all columns in all tables.
- **Column filters** — type in any column's filter input to narrow rows that contain the search term in that column.
- Click **Cancella filtri** to reset all filters.

### Editing Data Inline
- Click any cell value to edit it directly (the cell background turns yellow when modified).
- Click **Salva** next to the row to commit the change.

### Adding and Deleting Rows
- Click **+ Aggiungi riga** to add a new empty row at the bottom of a table.
- Fill in the values and click **Inserisci**.
- Click **Elimina** to delete a row (requires a primary key to identify the row).

### Exporting Data as CSV
- Click **Scarica CSV** to download the currently filtered view of a table as a CSV file.

---

## Step 7: Run Queries

Switch to the **Query** tab to explore your data using either natural language or direct SQL.

### Natural Language Queries
1. Type a question in plain language (e.g., "Which customers have spent more than 500 euros?").
2. Click **Generate SQL** — the AI converts your question into a SQL query.
3. Review the generated SQL and click **Execute** to run it.
4. Results appear in a table below.

### Direct SQL
1. Switch to the SQL editor.
2. Write or paste a SQL query.
3. Click **Execute**.

**Safety:** Write operations (INSERT, UPDATE, DELETE, DROP) are allowed but trigger an automatic backup first. SELECT queries do not create backups.

---

## Step 8: Export Full Database

1. On the Schema tab, click **Export** (near the edit button).
2. Choose an export format:
   - **SQL (DDL + INSERT)** — a complete SQL script with table creation and data insertion.
   - **JSON schema** — the schema definition in JSON format.
   - **CSV metadata** — the schema in tabular form (one row per column).
3. For the full SQL export, select a target dialect:
   - **SQLite** — standard SQLite syntax.
   - **PostgreSQL** — with SERIAL, BOOLEAN, and DOUBLE PRECISION types.
   - **MySQL** — with INT, TINYINT, and backtick quoting.
   - **Microsoft SQL Server** — with NVARCHAR, BIT, and DATETIME2 types.
4. Copy the exported SQL or save it to a file.

---

## Step 9: Backup and Restore

### Manual Backup
1. Click the **Backup** button on the Schema tab.
2. Optionally enter a label (e.g., "Before adding orders table").
3. The backup is saved as a `.db` file with timestamp and label.

### List Backups
- Click the dropdown next to the Backup button to see all backups with timestamps, labels, and file sizes.

### Restore
1. From the backup list, click **Ripristina** (Restore) on the desired backup.
2. The current database is overwritten with the backup. A pre-restore snapshot is automatically created in case you want to undo the restore.

### Automatic Backups
The system automatically creates a backup before:
- Populating tables
- Running a write query (INSERT, UPDATE, DELETE)
- Importing a SQL dump

---

## Step 10: Monitor Operation History

Click the **History** button on the Schema tab to view all logged operations for the current project. The timeline shows:

- Schema generations and edits
- Data population runs
- Query executions
- Backups and restores
- SQL imports

Each entry is timestamped and shows the event type. This history is primarily designed for research analysis but can help you understand what the system has done.

---

## Survey Forms (Experiment Participants Only)

If you are participating in a controlled experiment, you may be asked to complete:

1. **Raw NASA-TLX** — six 0–100 ratings in steps of 5; the aggregate workload score is their arithmetic mean.
2. **SUS** (System Usability Scale) — 10 standard statements rated 1–5 and converted to a single 0–100 score.

These appear at the bottom of the project page and are submitted automatically to the research data store. No personally identifying information is collected.
