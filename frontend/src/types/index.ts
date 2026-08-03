export interface ColumnDef {
  name: string
  data_type: string
  is_primary_key?: boolean
  is_foreign_key?: boolean
  foreign_key_table?: string
  foreign_key_column?: string
  is_unique?: boolean
  is_not_null?: boolean
  default_value?: string
  description?: string
}

export interface TableDef {
  name: string
  columns: ColumnDef[]
  description?: string
}

export interface RelationshipDef {
  type: 'one_to_many' | 'many_to_many' | 'one_to_one'
  from_table: string
  from_column: string
  to_table: string
  to_column: string
}

export interface NormalizedSchema {
  tables: TableDef[]
  relationships: RelationshipDef[]
  description?: string
}

export interface Project {
  id: string
  name: string
  prompt?: string
  schema_json?: NormalizedSchema
  db_path?: string
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  project_id: string
  filename: string
  file_type: string
  file_path?: string
  content_summary?: string
  created_at: string
  provenance?: {
    sha256?: string | null
    method?: string
    confidence?: number | null
  }
}

export interface GenerateRequest {
  prompt: string
  document_ids?: string[]
}

export interface QueryRequest {
  prompt: string
  dialect?: string
}

export interface QueryResponse {
  sql: string
  explanation?: string
}

export interface ExecuteQueryResponse {
  columns: string[]
  rows: Record<string, unknown>[]
  affected: number | null
}
