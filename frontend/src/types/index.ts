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
  owner_id?: string
  schema_finalized_at?: string | null
  owner_name?: string | null
  my_role?: 'owner' | 'editor' | 'viewer'
  step?: number
  status?: 'not_started' | 'schema_review' | 'data_ready'
  table_count?: number
  document_count?: number
  schema_version?: number
  target_dialect?: string | null
}

export interface Document {
  id: string
  project_id: string
  filename: string
  file_type: string
  file_path?: string
  content_summary?: string
  created_at: string
  needs_ocr?: boolean
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

export type JobKind = 'schema' | 'dati' | 'esportazione'
export type JobStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

export interface Job {
  id: string
  project_id: string
  kind: JobKind
  status: JobStatus
  progress: number
  error?: string | null
  result?: any
  created_at?: string
  updated_at?: string
}

export interface JobRequest {
  kind: JobKind
  prompt?: string
  document_ids?: string[]
  format?: 'sql' | 'json'
  dialect?: string
}

export type SchemaVersionOrigin = 'generazione' | 'chat' | 'manuale' | 'ripristino'

export interface SchemaVersionInfo {
  version: number
  author?: string | null
  origin: SchemaVersionOrigin | string
  created_at?: string
  table_count?: number
}

export interface SchemaVersionList {
  current: number
  finalized: boolean
  versions: SchemaVersionInfo[]
}

export interface QueryHistoryItem {
  id: string | number
  question?: string | null
  sql?: string | null
  source: 'query' | 'execute' | string
  outcome?: string | null
  rows?: number | null
  created_at?: string
}
