# API & Dataflow Map

## 1. API Endpoint Reference

### 1.1 Projects

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects` | Create a new project | `{name: str, prompt?: str}` | `{id, name, prompt, schema_json, db_path, created_at, updated_at}` |
| `GET` | `/api/projects` | List all projects | — | `[{id, name, prompt, created_at}]` |
| `GET` | `/api/projects/{id}` | Get project details | — | `{id, name, prompt, schema_json, db_path, created_at, updated_at}` |
| `DELETE` | `/api/projects/{id}` | Delete project | — | `{...project}` |

### 1.2 Documents

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects/{id}/documents` | Upload a document file | `multipart/form-data: file` | `{id, filename, file_type}` |
| `GET` | `/api/projects/{id}/documents` | List documents | — | `[{id, project_id, filename, file_type, created_at}]` |
| `DELETE` | `/api/projects/{id}/documents/{doc_id}` | Delete a document | — | `{...document}` |
| `POST` | `/api/projects/{id}/import-sql` | Import from SQL dump | `multipart/form-data: file` + `?dialect=` | `{tables: int, schema: NormalizedSchema}` |

### 1.3 Schema Generation

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects/{id}/generate` | Quick generate schema | `{prompt: str, document_ids: [str]}` | `NormalizedSchema` |
| `POST` | `/api/projects/{id}/chat` | Chat for schema generation | `{message: str, document_ids: [str]}` | `{response: str, schema?: NormalizedSchema}` |
| `POST` | `/api/projects/{id}/chat-accept` | Accept chat-generated schema | `NormalizedSchema` | `{...schema}` |
| `GET` | `/api/projects/{id}/schema` | Get current schema | — | `NormalizedSchema \| null` |
| `PUT` | `/api/projects/{id}/schema` | Update (edit) schema | `NormalizedSchema` | `{...updated_schema}` |
| `POST` | `/api/projects/{id}/generate-async` | Async schema generation | `{prompt: str, document_ids: [str]}` | `{task_id: str, status: "started"}` |

### 1.4 Data Population

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects/{id}/populate` | Populate from documents | `{document_ids: [str]}` | `{table_name: {inserted: int, skipped: int}}` |
| `POST` | `/api/projects/{id}/populate-async` | Async population | `{document_ids: [str]}` | `{task_id: str, status: "started"}` |

### 1.5 Data Operations

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/projects/{id}/data/stats` | Row counts per table | — | `{table_name: int}` |
| `GET` | `/api/projects/{id}/data/{table}` | Get table rows (max 100) | — | `[{col: value}]` |
| `PUT` | `/api/projects/{id}/data/{table}` | Update a row | `{col: value, ...}` (full row with PK) | `{updated: true}` |
| `DELETE` | `/api/projects/{id}/data/{table}` | Delete a row | `{pks: {pk_col: value}}` | `{deleted: true}` |
| `POST` | `/api/projects/{id}/data/{table}` | Insert a row | `{col: value, ...}` | `{inserted: true}` |

### 1.6 Queries

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects/{id}/query` | NL → SQL generation | `{prompt: str, dialect?: str}` | `{sql: str}` |
| `POST` | `/api/projects/{id}/execute-query` | Execute SQL | `{sql: str}` | `{columns: [str], rows: [dict], affected?: int}` |

### 1.7 Export

| Method | Path | Description | Query Params | Response |
|---|---|---|---|---|
| `GET` | `/api/projects/{id}/export` | Export schema | `?format=sql\|json\|csv` | `{format, content}` |
| `GET` | `/api/projects/{id}/export-full` | Export full DB | `?dialect=sqlite\|postgresql\|mysql\|mssql` | `{format, content, extension}` |
| `POST` | `/api/projects/{id}/export-async` | Async export | `?format=sql` | `{task_id, status}` |

### 1.8 Backup & Restore

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/projects/{id}/backup` | Create backup | `{label?: str}` | `{timestamp, label, file, size}` |
| `GET` | `/api/projects/{id}/backups` | List backups | — | `[{timestamp, label, file, size}]` |
| `POST` | `/api/projects/{id}/restore` | Restore from backup | `{backup_name: str}` | `{status: "restored", backup: str}` |

### 1.9 Metrics & Research

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/projects/{id}/metrics` | Compute quality metrics | — | `{norm3, relationships, data_quality}` |
| `POST` | `/api/projects/{id}/interactions` | Log an allowlisted interaction event | `{type, target_type, target_name, action?}` | `{status: "logged"}` |
| `GET` | `/api/projects/{id}/interactions` | Get interaction log | — | `[{timestamp, event_type, project_id, data}]` |
| `POST` | `/api/projects/{id}/export-interactions` | Export interactions as JSON | — | `{path, count}` |
| `POST` | `/api/experiments/compare` | Compare approaches | `{project_id, prompt, document_ids}` | `{automatic: {schema, metrics}}` |
| `POST` | `/api/surveys/nasa-tlx` | Submit NASA-TLX | `{project_id, mental_demand, ..., frustration}` | `{status, path}` |
| `POST` | `/api/surveys/sus` | Submit SUS | `{project_id, scores: [10 ints]}` | `{status, path, total_score}` |

### 1.10 System

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/health` | Health check | `{status: "ok"}` |
| `GET` | `/api/llm/info` | LLM provider info | `{provider: str, model: str}` |
| `GET` | `/api/tasks/{task_id}` | Task status (Celery) | `{task_id, status, result?}` |

---

## 2. Dataflow Diagram

The following describes how data flows through the system from initial document upload to final export. Backup points and logging touchpoints are annotated.

```
  USER                     FRONTEND                    BACKEND                        LLM                     STORAGE
   │                          │                          │                            │                        │
   │  1. Upload files         │                          │                            │                        │
   ├─────────────────────────>│                          │                            │                        │
   │                          │  POST /documents          │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Parse file (fitz/pandas)   │                        │
   │                          │                          │──────────────────────────────┼───────────────────────>│
   │                          │                          │                            │                        │  documents/ + app.db
   │                          │                          │  Log: document_upload      │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {id, filename}          │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │                          │                          │                            │                        │
   │  2. Generate schema      │                          │                            │                        │
   │  (chat or quick prompt)  │                          │                            │                        │
   ├─────────────────────────>│                          │                            │                        │
   │                          │  POST /generate           │                            │                        │
   │                          │  or POST /chat            │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Build prompt + doc_context │                        │
   │                          │                          ├───────────────────────────>│                        │
   │                          │                          │                            │  LLM inference         │
   │                          │                          │<───────────────────────────│                        │
   │                          │                          │                            │                        │
   │                          │                          │  Parse → NormalizedSchema   │                        │
   │                          │                          │  Log: schema_generated      │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {schema}                │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │  Review & edit           │                          │                            │                        │
   │<─────────────────────────│                          │                            │                        │
   │                          │                          │                            │                        │
   │  3. Save schema          │                          │                            │                        │
   ├─────────────────────────>│  PUT /schema              │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Create DB file            │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │                            │                        │  projects/{id}/database.sqlite
   │                          │                          │  Log: schema_saved          │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {updated_schema}        │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │                          │                          │                            │                        │
   │  4. Populate data        │                          │                            │                        │
   ├─────────────────────────>│  POST /populate           │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Auto-backup (before)      │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │                            │                        │  projects/{id}/backups/
   │                          │                          │                            │                        │
   │                          │                          │  Strategy A (tabular):     │                        │
   │                          │                          │  map_columns_to_tables()   │                        │
   │                          │                          ├───────────────────────────>│  LLM column mapping    │
   │                          │                          │<───────────────────────────│                        │
   │                          │                          │                            │                        │
   │                          │                          │  Strategy B (all docs):    │                        │
   │                          │                          │  generate_sql_for_pop()    │                        │
   │                          │                          ├───────────────────────────>│  LLM INSERT gen        │
   │                          │                          │<───────────────────────────│                        │
   │                          │                          │                            │                        │
   │                          │                          │  Execute INSERTs           │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │                            │                        │  database.sqlite
   │                          │                          │  Log: populate             │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {inserted_counts}       │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │                          │                          │                            │                        │
   │  5. Browse / CRUD        │                          │                            │                        │
   ├─────────────────────────>│  GET /data/{table}        │                            │                        │
   │                          │  PUT /data/{table}        │                            │                        │
   │                          │  POST /data/{table}       │                            │                        │
   │                          │  DELETE /data/{table}     │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Log: data_edit             │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {result}                │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │                          │                          │                            │                        │
   │  6. Natural Language Q   │                          │                            │                        │
   ├─────────────────────────>│  POST /query              │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          ├───────────────────────────>│  LLM SQL gen           │
   │                          │                          │<───────────────────────────│                        │
   │                          │  {sql}                   │                            │                        │
   │                          │<─────────────────────────│                            │                        │
   │  Execute                 │                          │                            │                        │
   ├─────────────────────────>│  POST /execute-query      │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Auto-backup if write      │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Execute SQL               │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Log: execute_query        │                        │
   │                          │                          │──┐                         │                        │
   │                          │  {columns, rows}         │  │                         │                        │
   │                          │<─────────────────────────│<─┘                         │                        │
   │                          │                          │                            │                        │
   │  7. Export               │                          │                            │                        │
   ├─────────────────────────>│  GET /export-full?dialect │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Read all rows from DB     │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Generate DDL + INSERT     │                        │
   │                          │                          │  (dialect-specific types)  │                        │
   │                          │  {content, format}       │                            │                        │
   │                          │<─────────────────────────│                            │                        │
   │                          │                          │                            │                        │
   │  8. Backup / Restore     │                          │                            │                        │
   ├─────────────────────────>│  POST /backup             │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  shutil.copy2(db → backup) │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Write metadata JSON       │                        │
   │                          │                          ├──────────────────────────────┼───────────────────────>│
   │                          │                          │  Log: backup               │                        │
   │                          │  {timestamp, file}       │                            │                        │
   │                          │<─────────────────────────│                            │                        │
   │                          │                          │                            │                        │
   │  9. Metrics              │                          │                            │                        │
   ├─────────────────────────>│  GET /metrics             │                            │                        │
   │                          ├─────────────────────────>│                            │                        │
   │                          │                          │  Compute 3NF score         │                        │
   │                          │                          │  Compute relationship F1   │                        │
   │                          │                          │  Compute data quality      │                        │
   │                          │  {norm3, rel, dq}        │  Save to project record    │                        │
   │                          │<─────────────────────────│                            │                        │
```

### Key Backup Points

```
B1 ──── Auto-backup before POPULATE (POST /populate)
B2 ──── Auto-backup before WRITE QUERY (POST /execute-query with INSERT/UPDATE/DELETE/DROP/CREATE/ALTER)
B3 ──── Auto-backup before SQL IMPORT (POST /import-sql)
B4 ──── Manual backup (POST /backup)
B5 ──── Pre-restore snapshot (inside POST /restore)
```

### Interaction Logging Touchpoints

Every box marked "Log:" writes an event to `projects/interactions_store.json` with `{timestamp, event_type, project_id, data}`. The following event types are logged:

- `document_upload` — file uploaded, filename and type recorded
- `document_delete` — file removed
- `schema_generated` — LLM produced a schema (chat or quick generate)
- `schema_accepted` — user accepted chat-generated schema
- `schema_saved` — user saved manual edits to schema
- `populate` — data population triggered, per-table counts
- `data_row_update` — row updated
- `data_row_insert` — row inserted
- `data_row_delete` — row deleted
- `execute_query` — SQL executed (SELECT vs. write, row/column counts)
- `backup` — manual backup with label
- `restore` — database restored from backup
- `import_sql` — SQL dump imported
- `survey_submitted` — NASA-TLX or SUS survey submitted
