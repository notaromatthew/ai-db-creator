export interface Stat { n: number; mean: number | null; low: number | null; high: number | null }

export interface RunRow {
  id: string; batch_id: string | null; dataset: string; condition: string; provider: string | null; model: string
  temperature: number | null; run_index: number; status: string; cancel_requested?: boolean
  f1: number | null; precision: number | null; recall: number | null; value_accuracy: number | null; judge_score: number | null
  tokens_in: number | null; tokens_out: number | null; cost_usd: number | null; latency_s: number | null
  error: string | null; created_at: string | null; started_at: string | null; finished_at: string | null
}

export interface RunDetail extends RunRow {
  per_table: Record<string, Record<string, number>> | null
  schema: { tables?: { name: string; columns?: { name: string; type?: string }[] }[] } | null
  manifest: Record<string, unknown> | null
}

export interface Group {
  dataset: string; condition: string; model: string; temperature: number | null; n_runs: number
  f1: Stat; precision: Stat; recall: Stat; value_accuracy: Stat; judge_score: Stat
  cost_usd_mean: number | null; cost_usd_total: number; latency_s_mean: number | null
  tokens_in_mean: number | null; tokens_out_mean: number | null
}

export interface Meta {
  datasets: string[]; conditions: string[]; models: { model: string; price_in_per_mtok: number; price_out_per_mtok: number; current: boolean }[]
  temperatures: number[]; cost_cap_usd: number; max_batch_runs: number; software_revision: string
  filters: { datasets: string[]; conditions: string[]; models: string[]; temperatures: number[] }
}

export interface Filters { dataset: string; condition: string; model: string; temperature: string }
export const NO_FILTERS: Filters = { dataset: '', condition: '', model: '', temperature: '' }

export const filterQuery = (f: Filters, extra: Record<string, string> = {}) => {
  const p = new URLSearchParams()
  Object.entries({ ...f, ...extra }).forEach(([k, v]) => { if (v !== '' && v != null) p.set(k, v) })
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const fmt = (v: number | null | undefined, digits = 3) =>
  v == null ? '—' : v.toLocaleString('it-IT', { minimumFractionDigits: digits, maximumFractionDigits: digits })
export const usd = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('it-IT', { minimumFractionDigits: 4, maximumFractionDigits: 4 })} $`)
export const CONDITION_LABEL: Record<string, string> = { full_llm: 'Schema e dati dall\'IA', baseline: 'Schema di riferimento' }
export const STATUS_LABEL: Record<string, string> = { queued: 'In coda', running: 'In corso', done: 'Completato', failed: 'Fallito', cancelled: 'Annullato' }

/** Scarica un testo come file (le esportazioni arrivano dal server già pronte). */
export function downloadText(filename: string, mime: string, content: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
