# 04 - API Dataflow & Data Contracts Handbook

> **Source Document**: `docs/09-api-dataflow-map.md`

---

## 1. Exhaustive API Endpoint Reference

### 1.1 Project Management (`/api/projects`)

| Method | Endpoint Path | Description | Request Body | Success Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/projects` | Create project | `{name: str, prompt?: str}` | `ProjectReadSchema` |
| `GET` | `/api/projects` | List user projects | None (Bearer Auth) | `List[ProjectReadSchema]` |
| `GET` | `/api/projects/{id}` | Get project by UUID | None | `ProjectDetailSchema` |
| `DELETE` | `/api/projects/{id}` | Delete project | None | `{status: "deleted"}` |

### 1.2 Document Ingestion & Import (`/api/projects/{id}/documents`)

| Method | Endpoint Path | Description | Content Type | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/projects/{id}/documents` | Upload CSV/PDF/XLSX | `multipart/form-data` | `DocumentReadSchema` |
| `GET` | `/api/projects/{id}/documents` | List uploaded docs | None | `List[DocumentReadSchema]` |
| `DELETE` | `/api/projects/{id}/documents/{doc_id}` | Delete document | None | `{status: "deleted"}` |
| `POST` | `/api/projects/{id}/import-sql` | Import raw SQL DDL | `multipart/form-data` | `{tables_imported: int}` |

### 1.3 Schema Generation & Refinement (`/api/projects/{id}/generate`)

| Method | Endpoint Path | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/projects/{id}/generate` | Sync 3NF schema generation | `{prompt: str, document_ids: List[str]}` | `NormalizedSchema` |
| `POST` | `/api/projects/{id}/chat` | Interactive schema chat | `{message: str}` | `{response: str, schema?: NormalizedSchema}` |
| `GET` | `/api/projects/{id}/schema` | Get active schema | None | `NormalizedSchema` |
| `PUT` | `/api/projects/{id}/schema` | Manual schema edit | `NormalizedSchema` | `NormalizedSchema` |

### 1.4 System Settings & Model Resolution (`/api/settings`)

| Method | Endpoint Path | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/settings` | Get current settings | None | `SettingsReadSchema` |
| `PUT` | `/api/settings` | Update settings & persist to `.env` | `SettingsUpdateSchema` | `SettingsReadSchema` |
| `GET` | `/api/settings/ollama-models` | Dynamic `/api/tags` resolution | `?base_url=&api_key=` | `{models: List[str]}` |
| `GET` | `/api/llm/info` | Active LLM info | None | `{provider: str, model: str}` |

---

## 2. Core Pydantic Schemas (`app/models/schema_models.py`)

### `NormalizedSchema` Schema
```json
{
  "tables": [
    {
      "name": "string",
      "columns": [
        {
          "name": "string",
          "data_type": "INTEGER | VARCHAR | TEXT | FLOAT | BOOLEAN | DATETIME",
          "is_primary_key": true,
          "is_foreign_key": false,
          "foreign_key_table": null,
          "foreign_key_column": null,
          "is_unique": false,
          "is_not_null": true
        }
      ]
    }
  ],
  "relationships": [
    {
      "type": "one-to-many | many-to-many",
      "from_table": "string",
      "from_column": "string",
      "to_table": "string",
      "to_column": "string"
    }
  ]
}
```
