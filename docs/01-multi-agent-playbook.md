# Multi-Agent Playbook: Epistemic Decomposition

Although AI-DB-Creator does not implement explicit software agents (no agent orchestration framework, no message bus, no agent registry), its architecture can be usefully decomposed into seven **epistemic roles** — functional boundaries that correspond to distinct knowledge domains, input/output contracts, and failure modes. This decomposition guides debugging, extension, and research analysis.

---

## Agent 1: Document Ingestion Agent

| Aspect | Description |
|---|---|
| **Purpose** | Accept uploaded files of heterogeneous formats, extract raw text and tabular structure, and produce a uniform representation for downstream agents. |
| **Epistemic role** | Knows how to interpret file formats — PDF layouts, Excel sheets with multiple tabs, CSV with varying delimiters and encodings, plain text. |
| **Inputs** | Binary file upload (`UploadFile`), file type hint from extension (.pdf, .xlsx, .csv, .txt, .sql), project ID. |
| **Outputs** | `ParsedDocument` objects containing: filename, full text content (string), and an optional list of tabular structures (list-of-lists with headers). Stored in the `documents` SQLAlchemy table with a `content_summary` field. |
| **Technology** | `app/core/parser.py` — Parser factory pattern. PyMuPDF (`fitz`) for PDF, `pandas` + `openpyxl`/`xlrd` for Excel, `pandas` with encoding/delimiter detection for CSV. |
| **Failure modes** | **PDF with embedded images only** → empty text content. **Corrupted Excel files** → `ParsingException`. **CSV with undetectable encoding** → returns empty text after exhausting 4 encodings x 5 delimiters. **Large unstructured documents** → LLM-bound text is limited to 5,000 characters per document, creating a measurable risk of omitted information. |
| **Recovery** | The parser never raises exceptions to the API; it catches all and returns empty text. The user sees the file listed but the LLM receives no content. |

---

## Agent 2: Schema Generation Agent

| Aspect | Description |
|---|---|
| **Purpose** | From user descriptions and document content, infer a 3NF-normalised relational schema with tables, columns, types, keys, and constraints. |
| **Epistemic role** | Knows relational theory (normal forms, candidate keys, functional dependencies, referential integrity). Can map real-world concepts to normalised structures. |
| **Inputs** | User prompt (free text, e.g., "a university with students and courses"), bounded document summaries (up to 5,000 characters per document), LLM provider configuration. |
| **Outputs** | `NormalizedSchema` Pydantic model: `list[TableDef]` (each with `list[ColumnDef]`), `list[RelationshipDef]`, and an optional description. |
| **Technology** | `app/core/llm.py` — LangChain `ChatPromptTemplate` + PydanticOutputParser bound to `NormalizedSchema`. The prompt instructs the LLM to produce 3NF tables, snake_case names, primary keys on every table, and foreign keys referencing existing tables. |
| **Failure modes** | **LLM hallucination** — generates plausible but semantically wrong tables or relationships (e.g., creating a "professors" table when the data mentions only "teachers"). **Inconsistent naming** — same concept named differently across runs. **Missing constraints** — LLM omits foreign keys or NOT NULL despite prompt instructions. **Schema too large** — LLM context window exceeded when many documents are attached. **Parse failure** — LLM output does not conform to `NormalizedSchema` JSON schema → `LLMException`. |
| **Recovery** | The chat interface allows iterative refinement: the user can request changes in natural language, and the agent regenerates with the full conversation history. |

---

## Agent 3: Database Creation Agent

| Aspect | Description |
|---|---|
| **Purpose** | Translate the logical `NormalizedSchema` into a physical SQLite database file on disk using SQLAlchemy ORM. |
| **Epistemic role** | Knows SQL DDL, type mappings, and SQLAlchemy Metadata/Table creation. Has no understanding of the domain; it is purely mechanical. |
| **Inputs** | `NormalizedSchema` object, target `db_path` (file system path). |
| **Outputs** | SQLite database file at `projects/{project_id}/database.sqlite`. Returns the `db_path` string. |
| **Technology** | `app/core/db_generator.py` — `create_database_from_schema()` maps each `ColumnDef.data_type` string to a SQLAlchemy type via `TYPE_MAP`, builds `Table` objects with `Column`, `ForeignKey`, `UniqueConstraint`, and nullable flags, then calls `metadata.create_all(engine)`. |
| **Failure modes** | **Foreign key order dependency** — if table A references table B but B is defined after A in the schema list, SQLite may fail (mitigated by SQLite's deferred FK enforcement). **Path permission errors** — the `projects/` directory must be writable. **Concurrent creation** — no locking; two rapid schema updates could race. |
| **Recovery** | The agent deletes and recreates on schema update. An auto-backup of the old `.db` file is taken before recreation. |

---

## Agent 4: Data Population Agent

| Aspect | Description |
|---|---|
| **Purpose** | Extract data from uploaded documents and insert it into the generated database tables, respecting foreign key constraints and NOT NULL rules, using the LLM as the primary population route for all document types. |
| **Epistemic role** | Knows how to interpret denormalised document data and map it to a normalised relational structure. Can perform two distinct reasoning tasks: (a) column-to-table mapping for tabular documents, and (b) bulk INSERT generation for all documents. |
| **Inputs** | Project ID, database path, approved `NormalizedSchema`, list of document IDs to process. |
| **Outputs** | Dictionary mapping table names to `{inserted: int, skipped: int}` counts. The database file is mutated in place. |
| **Technology** | One primary strategy in `app/services/population_service.py`:

**Strategy A (bulk LLM SQL generation, primary):** `generate_sql_for_population()` feeds the full schema DDL + the complete content of every document (CSV, Excel, PDF, TXT) to the LLM, which returns a block of `INSERT OR IGNORE` statements. These are executed via raw SQLAlchemy `text()`. The LLM overrides any deterministic matching and decides how to map values; duplicates already present in the target tables are ignored, and NULL/empty values are accepted where the schema allows them.

**Strategy B (tabular mapping, fallback):** If the LLM returns no usable SQL, for documents with tabular structure (CSV/Excel) the LLM `map_columns_to_tables()` function receives the document headers + sample rows + schema definition and returns a mapping like `{"clienti": {0: "codice_fiscale", 1: "nome"}}`, merged with exact/partial header rules; data is then inserted row by row. |
| **Failure modes** | **Wrong column mapping** — LLM maps "Name" to "indirizzo" instead of "nome". **Missing FK references** — LLM generates INSERTs that violate foreign keys. **Duplicate data** — same entity inserted multiple times if documents overlap. **PDF text extraction artefacts** — garbled text leads to nonsense data. **NULL on NOT NULL column** — LLM generates NULL for a column marked NOT NULL, causing INSERT failure. **Context window overflow** — very large documents are truncated. |
| **Recovery** | Population is idempotent (`INSERT OR IGNORE`). Users can re-populate after editing the schema. An auto-backup is taken before each population. |

---

## Agent 5: Validation Agent

| Aspect | Description |
|---|---|
| **Purpose** | Provide the human-in-the-loop interface for reviewing, editing, and approving the generated schema and data. |
| **Epistemic role** | Knows nothing about the domain itself; it is a presentation layer that enables the human expert to apply their own domain knowledge. |
| **Inputs** | `NormalizedSchema` from Schema Agent, `table_data` from the database, user edit actions (add/remove table, add/remove column, toggle PK/FK/NN, edit cell values). |
| **Outputs** | Updated `NormalizedSchema` (via `PUT /projects/{id}/schema`), updated row data (via `PUT/DELETE/POST /projects/{id}/data/{table}`). |
| **Technology** | **SchemaViewer.tsx** — renders tables as cards with column grids; edit mode provides inline inputs, checkboxes for constraints, and add/remove buttons. **DataViewer.tsx** — renders table data with inline editing, column filters, global search, CSV export, add/delete rows. |
| **Failure modes** | **User error** — user introduces inconsistent schema (e.g., removes a column that is a foreign key reference). **UI/UX confusion** — non-expert users may not understand PK/FK concepts and make incorrect edits. **No undo for schema edits** — once saved, schema changes are applied as DDL migrations (add columns only; no column removal migration). |
| **Recovery** | Schema changes are applied via `migrate_database()` which only adds new tables/columns (never drops). Old data is preserved. Backups allow full rollback. |

---

## Agent 6: Export Agent

| Aspect | Description |
|---|---|
| **Purpose** | Serialize the entire database (schema + data) as a portable SQL script targeting different SQL dialects. |
| **Epistemic role** | Knows SQL dialect differences — type mappings, quoting conventions, boolean representations, identity/serial syntax, constraint placement. |
| **Inputs** | Project ID, target dialect (`sqlite`, `postgresql`, `mysql`, `mssql`), schema definition, database file path. |
| **Outputs** | String containing DDL (CREATE TABLE with dialect-specific types, NOT NULL, PK, FK, UNIQUE) followed by INSERT statements for every row. |
| **Technology** | `app/core/db_export.py` — `export_full()` iterates schema tables, generates `_generate_create_table()` per dialect using `TYPE_MAP`, then reads all rows from the SQLite source and generates dialect-appropriate INSERTs via `_escape_val()`. |
| **Failure modes** | **Unmapped type** — a custom data type not in `TYPE_MAP` defaults to TEXT, which may be incorrect. **Dialect-specific syntax** — MySQL's backtick quoting vs. SQLite's bracket quoting vs. PostgreSQL's double-quote quoting; the export currently uses brackets which fail on PostgreSQL/MySQL. **Very large exports** — no streaming; the entire export is built in memory. |
| **Recovery** | The exported SQL is returned as a text blob; users can inspect and manually correct before using. |

---

## Agent 7: Backup Agent

| Aspect | Description |
|---|---|
| **Purpose** | Create point-in-time snapshots of the project database and restore previous states. |
| **Epistemic role** | Knows file system operations and snapshot management. Purely mechanical. |
| **Inputs** | Database path, project ID, optional label, backup name (for restore). |
| **Outputs** | Backup file at `{db_parent}/backups/{timestamp}_{label}.db`, metadata JSON sidecar. |
| **Technology** | `app/services/backup_service.py` — `shutil.copy2()` for file-level snapshots. Automatic backups triggered before: population, query execution (write operations), SQL import. |
| **Failure modes** | **Disk space exhaustion** — large databases with many backups fill the disk. **Concurrent backup during write** — no file locking; a backup taken during a write could be corrupt. **Backup metadata drift** — if the database file is moved, backups become orphaned. |
| **Recovery** | The `restore_backup()` method creates an "undo" snapshot before overwriting the current database, so every restore is reversible. |
