import { api } from './client'

export interface ColumnDef {
  name: string
  data_type: string
  flags: string[]
  is_primary_key: boolean
  is_unique: boolean
  is_not_null: boolean
  is_foreign_key: boolean
  foreign_key_target?: string | null
}

export interface TableDef {
  name: string
  columns: ColumnDef[]
}

export interface RelationshipDef {
  from: string
  type: string
  to: string
}

export interface ExpertRating {
  d1_3nf: number
  d2_naming: number
  d3_constraints: number
  d4_relationships: number
  d5_domain: number
  comment?: string | null
  updated_at?: string | null
}

export interface ExpertSchema {
  code: string
  title: string
  description: string
  tables: TableDef[]
  relationships: RelationshipDef[]
  table_count: number
  column_count: number
  relationship_count: number
  raw_markdown: string
  has_evaluated: boolean
  rating?: ExpertRating
}

export interface EvaluationSubmission {
  evaluator_name: string
  schema_code: string
  d1_3nf: number
  d2_naming: number
  d3_constraints: number
  d4_relationships: number
  d5_domain: number
  comment?: string | null
}

export interface AdminDimensionMeans {
  count: number
  d1_3nf: number
  d2_naming: number
  d3_constraints: number
  d4_relationships: number
  d5_domain: number
  overall: number
}

export interface EvaluatorProgress {
  evaluator_name: string
  completed: number
  total: number
  progress_percent: number
}

export interface AdminEvaluationRecord {
  id: string
  evaluator_name: string
  schema_code: string
  dataset: string
  condition: string
  run: string
  d1_3nf: number
  d2_naming: number
  d3_constraints: number
  d4_relationships: number
  d5_domain: number
  average_score: number
  comment: string
  created_at: string | null
  updated_at: string | null
}

export interface AdminSchemaSummary {
  code: string
  dataset: string
  condition: string
  run: string
  evaluations_count: number
  avg_score: number | null
}

export interface AdminDashboardData {
  total_schemas: number
  total_evaluations: number
  unique_evaluators_count: number
  evaluator_progress: EvaluatorProgress[]
  overall_means: AdminDimensionMeans
  condition_comparison: {
    baseline: AdminDimensionMeans
    full_llm: AdminDimensionMeans
  }
  dataset_comparison: {
    hospital: AdminDimensionMeans
    library: AdminDimensionMeans
    university: AdminDimensionMeans
  }
  schema_summary: AdminSchemaSummary[]
  evaluations: AdminEvaluationRecord[]
}

const getApiBase = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL
  if (typeof window !== 'undefined' && window.location?.origin) return window.location.origin
  return 'http://localhost:8000'
}

export const expertApi = {
  async listSchemas(evaluatorName?: string): Promise<ExpertSchema[]> {
    const q = evaluatorName ? `?evaluator_name=${encodeURIComponent(evaluatorName)}` : ''
    return api.get(`/expert/schemas${q}`)
  },

  async getSchema(code: string, evaluatorName?: string): Promise<ExpertSchema> {
    const q = evaluatorName ? `?evaluator_name=${encodeURIComponent(evaluatorName)}` : ''
    return api.get(`/expert/schemas/${code}${q}`)
  },

  async submitEvaluation(payload: EvaluationSubmission): Promise<any> {
    return api.post('/expert/evaluations', payload)
  },

  async verifyAdminKey(adminKey: string): Promise<{ valid: boolean; message: string }> {
    return api.post('/admin/verify', { admin_key: adminKey })
  },

  async getAdminDashboard(adminKey: string): Promise<AdminDashboardData> {
    const res = await fetch(`${getApiBase()}/api/admin/expert-evaluations`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': adminKey,
      },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Errore autenticazione admin' }))
      throw new Error(err.detail || 'Richiesta non autorizzata')
    }
    return res.json()
  },

  getExportCsvUrl(adminKey: string): string {
    return `${getApiBase()}/api/admin/expert-evaluations/export?admin_key=${encodeURIComponent(adminKey)}`
  },
}
