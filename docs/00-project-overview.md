# AI-DB-Creator: Project Overview

## 1. What Is AI-DB-Creator?

AI-DB-Creator is an LLM-powered visual interface that enables non-expert users to automatically generate normalized relational database schemas and populate them with data extracted from heterogeneous documents. The system combines a React + TailwindCSS frontend with a FastAPI Python backend and uses a configurable Large Language Model (LLM) — currently supporting OpenAI, Google Gemini, Groq, OpenRouter, and local Ollama models — to perform schema design, data extraction, and natural-language-to-SQL translation.

The resulting database can be explored through an interactive CRUD interface, queried in natural language, and exported as DDL + INSERT statements for SQLite, PostgreSQL, MySQL, and Microsoft SQL Server.

## 2. The Problem

Relational database design is a highly skilled task requiring knowledge of normalization theory (3NF, BCNF), entity-relationship modelling, foreign key constraints, data type selection, and SQL DDL syntax. Many professionals who work with structured data — researchers in the humanities and social sciences, domain experts in biology or geology, small business operators managing inventory or customer records — lack the technical background to create relational databases from scratch.

Existing tools fall into three categories, all inadequate for this audience:

- **Visual designers (MySQL Workbench, pgAdmin, DBeaver):** require the user to already understand relational modelling; they visualise but do not design.
- **Low-code/no-code platforms (Airtable, Notion,Retool):** abstract away SQL but do not produce portable relational databases with enforced constraints, foreign keys, or normalised structure.
- **LLM-based code generators:** can produce SQL DDL from a description, but the output is a single-shot text blob with no visual review, no iterative refinement, no multi-document ingestion, and no data population.

AI-DB-Creator bridges this gap by combining LLM reasoning with a human-in-the-loop visual interface [1,2,3].

## 3. Target Users

| User Profile | Use Case | Technical Background |
|---|---|---|
| **Researchers** (humanities, social sciences, bioinformatics) | Model experimental data, survey results, or archival records as a queryable relational DB | Comfortable with files and spreadsheets; no SQL |
| **Domain experts** (geologists, biologists, archivists) | Structure domain-specific observations into normalised tables with cross-references | Familiar with their data model but not with database tools |
| **Small business operators** | Convert inventory lists, customer registers, or invoice records from Excel into a proper database | Comfortable with office software; no database training |
| **CS educators** | Demonstrate database design and normalisation concepts interactively | Teach database topics; may use the tool as a teaching aid |

## 4. Key Features

### 4.1 LLM-Powered Schema Generation
The user describes their domain (e.g., "a university with students, courses, professors, and enrollments") or uploads source documents. The LLM infers a 3NF-normalised schema with tables, columns, primary keys, foreign keys, unique constraints, NOT NULL constraints, and data types.

### 4.2 Automatic Data Population
Once the schema is approved, the current implementation supplies bounded parsed document summaries to the configured population path; `Document.content_summary` is truncated to 5,000 characters. It therefore does **not** guarantee that complete uploaded documents reach the LLM. LLM population and deterministic fallback are recorded in provenance and evaluated separately; neither route is assumed accurate without benchmark evidence.
- **LLM primary:** the full document is passed to the model, which emits `INSERT` statements per table; duplicates already in the database are ignored.
- **Deterministic fallback:** if the LLM returns no usable SQL, exact/partial header rules map known columns; unresolved ones may use semantic LLM mapping (`hybrid`).
- **Traceability:** population results expose the extraction method (`llm`, `deterministic`, or `hybrid`) and source coordinates; confidence is shown only when it is explicitly available and is labelled as uncalibrated unless validated on held-out data.

### 4.3 Visual CRUD Interface
Users can browse table data, search across all tables (global text search), filter individual columns, edit cells in-line, add new rows, and delete existing rows — all from the browser, without writing SQL.

### 4.4 Multi-Dialect Export
Generated databases can be exported as full DDL + INSERT scripts for four SQL dialects: SQLite, PostgreSQL, MySQL, and Microsoft SQL Server. The type mapping system handles dialect-specific data types, quoting, and boolean representations.

### 4.5 Backup and Restore
Automatic snapshots are taken before destructive operations (population, query execution, SQL import). Users can also create manual backups with labels and restore any previous state.

### 4.6 Natural Language Querying
Users can describe the data they want in plain language (e.g., "Show me all students enrolled in more than 3 courses") and the LLM generates the corresponding SQL, which can be executed directly.

### 4.7 Research Metrics
The system computes schema quality metrics (3NF compliance score, relationship precision/recall/F1), data quality metrics (duplicate counts, record counts), and logs all user interactions for research analysis.

### 4.8 Survey Integration
Built-in NASA-TLX (cognitive load) and SUS (System Usability Scale) survey forms for collecting participant feedback during controlled experiments.

## 5. Technology Stack

### Frontend

| Layer | Technology | Purpose |
|---|---|---|
| Framework | React 18 + TypeScript | Component-based UI |
| Build | Vite 5 | Fast dev server and bundling |
| Styling | TailwindCSS 3 | Utility-first responsive design |
| Routing | react-router-dom v6 | Client-side navigation |
| Data Fetching | @tanstack/react-query v5 | Server state, caching, mutations |
| Diagram | ReactFlow | ER-diagram visualisation (optional) |

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| Framework | FastAPI 0.115 | Async REST API, auto-docs |
| ASGI Server | Uvicorn 0.30 | Production server |
| ORM | SQLAlchemy 2.0 | App state DB (SQLite), dynamic DB creation |
| LLM Integration | LangChain (OpenAI, Ollama, Google GenAI, Groq) | Provider-agnostic LLM calls |
| Validation | Pydantic / Pydantic-Settings | Request validation, configuration |
| Document Parsing | PyMuPDF (PDF), pandas/openpyxl/xlrd (Excel), csv | Heterogeneous file ingestion |
| Background Tasks | Celery + Redis | Async schema generation and population |
| Rate Limiting | slowapi | API abuse prevention |
| Logging | Loguru | Structured logging |

### LLM Providers

| Provider | Model | Use Case |
|---|---|---|
| OpenAI (default) | gpt-4o-mini | Schema generation, population, query |
| Google Gemini | gemini-2.0-flash | Same, via langchain-google-genai |
| Groq | llama3-70b-8192 | Same, via OpenAI-compatible endpoint |
| OpenRouter | configurable | Same, via OpenAI-compatible endpoint |
| Ollama (local) | llama3 (auto-detected) | Offline/private operation |

## 6. Research Positioning

AI-DB-Creator is **not a commercial product**. It is a **PhD research platform** designed to investigate the following research questions:

- **RQ0:** How does the complete AI + Interface workflow compare with a fully manual process for non-expert users?
- **RQ1:** How does the quality of LLM-generated schemas compare to manually created gold-standard schemas, as judged by database experts?
- **RQ2:** How accurate is LLM-driven automatic data population at the cell level, measured against ground-truth data?
- **RQ3:** Does a human-in-the-loop visual interface improve schema quality compared to an automatic-only approach?
- **RQ4:** What interaction patterns emerge when non-expert users design databases via an LLM-powered interface?

The system supports a **three-arm between-subjects controlled experiment**: Manual, AI-Only, and AI + Interface. Manual vs. AI + Interface answers the overarching RQ0 comparison; AI-Only vs. AI + Interface isolates the human-in-the-loop contribution for RQ3.

## 7. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────────┐   │
│  │ Dashboard │ │ Project  │ │ Data   │ │ Query Builder │   │
│  │           │ │ Page     │ │ Viewer │ │               │   │
│  └──────────┘ └──────────┘ └────────┘ └───────────────┘   │
│       │              │            │              │          │
│       └──────────────┴────────────┴──────────────┘          │
│                         │ HTTP (REST)                       │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│              FASTAPI BACKEND (Uvicorn)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Routes (/api/*)                                  │   │
│  │  Projects | Documents | Schema | Population | Query   │   │
│  │  Export/Import | Backup/Restore | Metrics | Surveys   │   │
│  └──────────────────────────────────────────────────────┘   │
│           │              │              │                    │
│  ┌────────▼──────┐ ┌────▼──────┐ ┌─────▼─────────────┐     │
│  │ Schema Service│ │Population │ │ Document Service    │     │
│  │ (LLM prompt)  │ │Service    │ │ (Parser Factory)    │     │
│  └───────────────┘ └───────────┘ └────────────────────┘     │
│           │              │              │                    │
│  ┌────────▼──────────────▼──────────────▼────────────┐      │
│  │               LangChain LLM Layer                    │     │
│  │  OpenAI │ Google Gemini │ Groq │ Ollama │ OpenRouter│     │
│  └────────────────────────────────────────────────────┘      │
│           │                                                   │
│  ┌────────▼────────────────────────────────────────────┐      │
│  │  SQLAlchemy / SQLite (Project DB & Generated DBs)    │     │
│  └─────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

The data flow through the system proceeds as:

1. **Document Ingestion:** User uploads files (CSV, XLSX, PDF, TXT, SQL) via the browser. The backend parses each file with the appropriate parser (PyMuPDF for PDF, pandas for Excel/CSV, plain text for TXT/SQL). Parsed text content and tabular structures are stored in the project's document registry.

2. **Schema Generation:** The user describes the domain via chat or a quick-prompt field. The LLM (LangChain chain with Pydantic output parser) returns a `NormalizedSchema` object with tables, columns, relationships, and constraints. The schema is stored as JSON in the project record.

3. **Database Creation:** When the user approves the schema, SQLAlchemy `metadata.create_all()` generates the SQLite database file at the project path.

4. **Data Population:** The LLM reads the document text and the approved schema, then generates INSERT statements. The service executes these against the project's SQLite file with foreign key enforcement.

5. **Exploration & Export:** Users explore data through the CRUD interface, run NL-to-SQL queries, and export the full database as multi-dialect DDL + INSERT scripts.

6. **Backup:** Before each destructive operation, `BackupService.auto_backup()` copies the current `.db` file to a timestamped backup.

7. **Metrics & Logging:** Every user interaction is timestamped and persisted to an interactions store. Schema quality metrics (3NF, relationship F1) and data quality metrics (duplicates, record counts) are computed on demand.

---

## 8. References

[1] E. F. Codd. "A Relational Model of Data for Large Shared Data Banks." *Communications of the ACM*, 13(6):377–387, 1970. (Origin of the relational model; basis for the normalisation terminology 3NF/BCNF used throughout.)

[2] P. A. Bernstein and S. Melnik. "The Case for a Spreadsheet-Database Integration." *Communications of the ACM*, 54(7):80–88, 2011. (Documents the spreadsheet-vs-relational gap that motivates the target user population.)

[3] S. Chaudhuri, N. Chhetri, and A. Neupane. "NL2Schema: Generating Database Schemas from Natural Language Descriptions." arXiv:2310.05978, 2023.

[4] Y. Zhang et al. "Schema Matching using Large Language Models." arXiv:2310.11779, 2023.

[5] E. Rahm and P. A. Bernstein. "A Survey of Approaches to Automatic Schema Matching." *The VLDB Journal*, 10(4):334–350, 2001.

[6] S. G. Hart and L. E. Staveland. "Development of NASA-TLX (Task Load Index)." *Human Mental Workload*, pages 139–183, 1988.

[7] J. Brooke. "SUS: A Quick and Dirty Usability Scale." *Usability Evaluation in Industry*, pages 189–194, 1996.

*See also `08-research-notes.md` and `11-benchmark-protocol.md` for the full reference list and how each citation maps to the research design.*
