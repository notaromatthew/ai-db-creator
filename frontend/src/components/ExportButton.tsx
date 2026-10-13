import { useState } from 'react'
import { api } from '@/api/client'
import { dialectLabel, type Dialect } from '@/components/flow/DialectPicker'

function saveFile(name: string, content: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** Scarica schema e dati come script SQL nel dialetto scelto. */
export async function downloadScript(projectId: string, dialect: Dialect) {
  const data = await api.get(`/projects/${projectId}/export-full?dialect=${dialect}`)
  saveFile(`db_${projectId}_${dialect}.${data.extension || 'sql'}`, data.content, 'text/sql')
}

/** Scarica una tabella intera come CSV (lettura completa, non l'anteprima da 100 righe). */
export async function downloadTableCsv(projectId: string, table: string) {
  const res = await api.post(`/projects/${projectId}/execute-query`, { sql: `SELECT * FROM [${table}]` })
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v)
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [res.columns.map(esc).join(',')]
  for (const row of res.rows as Record<string, unknown>[]) lines.push(res.columns.map((c: string) => esc(row[c])).join(','))
  saveFile(`${table}.csv`, lines.join('\n') + '\n', 'text/csv')
}

interface Props {
  projectId: string
  dialect: Dialect
  className?: string
}

export default function ExportButton({ projectId, dialect, className = 'primary-button' }: Props) {
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  const handleClick = async () => {
    setExporting(true)
    setError('')
    try {
      await downloadScript(projectId, dialect)
    } catch (e: any) {
      setError(e?.message || 'Non è stato possibile preparare lo script.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <button type="button" onClick={handleClick} disabled={exporting} className={className}>
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">download</span>
        {exporting ? 'Preparo lo script…' : `Scarica lo script per ${dialectLabel(dialect)}`}
      </button>
      {error && <p role="alert" className="w-full text-sm text-red-600">{error}</p>}
    </>
  )
}
