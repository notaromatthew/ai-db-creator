# 01 - Project Overview & Target User Profiles

> **Source Documents**: `docs/00-project-overview.md`, `docs/03-user-manual.md`

---

## 1. Executive Summary & Scientific Purpose

**AI-DB-Creator** is an LLM-powered visual platform designed to assist non-expert users in generating normalized relational database schemas (3NF) and populating them from heterogeneous files (CSV, Excel, PDF, TXT).

It combines a React 18 + TypeScript + TailwindCSS frontend with a FastAPI Python backend and supports a multi-provider LLM orchestration layer (Remote/Local Ollama, Google Gemini, OpenAI, Groq, OpenRouter).

---

## 2. Core Problem Statement

Traditional relational database design requires deep expertise in normalization theory (1NF, 2NF, 3NF, BCNF), entity-relationship modeling, foreign key constraints, and SQL DDL syntax.

Existing software tools fail non-expert domain experts (humanities researchers, geologists, archivists, small business operators):
- **Visual DB Designers** (MySQL Workbench, pgAdmin): Require prior knowledge of relational algebra and manual entity modeling.
- **No-Code Platforms** (Airtable, Notion): Abstract away SQL but do not produce normalized relational schemas with strict FK enforcement and SQL export capabilities.
- **LLM Text Code Generators**: Produce single-shot SQL text without visual interactive CRUD, iterative chat refinement, multi-document parsing, or data population.

AI-DB-Creator bridges this gap by marrying LLM reasoning with a human-in-the-loop visual interface.

---

## 3. Target User Personas

| User Profile | Primary Goal | Technical Background |
| :--- | :--- | :--- |
| **Academic Researchers** (Humanities, BioInformatics, Social Sciences) | Convert survey results, unstructured interviews, or archival catalogs into structured queryable databases | Comfortable with files and spreadsheets; zero SQL knowledge |
| **Domain Experts** (Archivists, Geologists, Biologists) | Structure domain observations into normalized tables with cross-references | High domain knowledge; unfamiliar with relational modeling |
| **Small Business Operators** | Migrate Excel inventory lists, customer registers, or sales ledgers into a production relational database | Comfortable with Office tools; no formal database training |
| **Computer Science Educators** | Demonstrate 3NF normalization, ER modeling, and SQL queries interactively | CS teaching staff; use app as an interactive educational aid |

---

## 4. Key Functional Features

1. **LLM-Powered Schema Generation**: Infers 3NF normalized tables, primary keys, foreign keys, unique constraints, and NOT NULL flags from natural language or uploaded documents.
2. **Full-LLM Data Ingestion & Population**: Passes documents directly to the LLM for schema mapping and `INSERT` statement generation with duplicate suppression.
3. **Visual Interactive CRUD**: Browse tables, perform global text searches, filter columns, inline edit cells, and manage records without writing raw SQL.
4. **Multi-Dialect SQL Export**: Exports complete DDL + INSERT scripts for **PostgreSQL**, **SQLite**, **MySQL**, and **Microsoft SQL Server**.
5. **Snapshot Backup & Restore**: Takes automated safety snapshots before destructive operations and supports manual point-in-time restore.
6. **Natural Language to SQL Querying**: Translates user prompts into executable SQL queries with real-time result tables.
