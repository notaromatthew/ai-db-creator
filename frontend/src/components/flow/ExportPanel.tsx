import { useState } from 'react'
import DialectPicker, { type Dialect } from './DialectPicker'
import ExportButton, { downloadTableCsv } from '@/components/ExportButton'
import { NormalizedSchema } from '@/types'

interface Props {
  projectId: string
  schema: NormalizedSchema
  dialect: Dialect
  onDialectChange: (d: Dialect) => void
  queryOpen: boolean
  onToggleQuery: () => void
  /** Rigenera i dati: nascosto ai lettori. */
  onRegenerate?: () => void
  regenerating?: boolean
}

export default function ExportPanel({ projectId, schema, dialect, onDialectChange, queryOpen, onToggleQuery, onRegenerate, regenerating }: Props) {
  const [csvOpen, setCsvOpen] = useState(false)
  const [csvBusy, setCsvBusy] = useState<string | null>(null)
  const [csvError, setCsvError] = useState('')

  const exportCsv = async (tables: string[]) => {
    setCsvError('')
    try {
      for (const t of tables) {
        setCsvBusy(t)
        await downloadTableCsv(projectId, t)
      }
    } catch (e: any) {
      setCsvError(e?.message || 'Non è stato possibile preparare il CSV.')
    } finally {
      setCsvBusy(null)
    }
  }

  return (
    <section className="glass flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="export-title">
      <div>
        <h3 id="export-title" className="text-lg font-bold">Per quale database vuoi lo script?</h3>
        <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">Adatto tipi di dato e sintassi al sistema che userai. La scelta resta salvata nel progetto: puoi cambiarla e riscaricare quando vuoi.</p>
      </div>
      <DialectPicker value={dialect} onChange={onDialectChange} />
      <div className="flex flex-wrap items-center gap-3">
        <ExportButton projectId={projectId} dialect={dialect} />
        <button type="button" className="secondary-button" aria-expanded={csvOpen} onClick={() => setCsvOpen((v) => !v)}>
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">folder_zip</span>CSV per tabella
        </button>
        <button type="button" className="secondary-button" aria-pressed={queryOpen} onClick={onToggleQuery}>
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">terminal</span>Interroga con una domanda
        </button>
        {onRegenerate && (
          <button type="button" className="secondary-button" onClick={onRegenerate} disabled={regenerating}>
            <span className={`material-symbols-outlined text-[18px] ${regenerating ? 'animate-spin' : ''}`} aria-hidden="true">refresh</span>
            {regenerating ? 'Rigenero…' : 'Rigenera i dati'}
          </button>
        )}
      </div>
      {csvOpen && (
        <div className="flex flex-wrap gap-2 rounded-xl border border-tecnia-line/60 p-3 dark:border-slate-700">
          {schema.tables.map((t) => (
            <button key={t.name} type="button" className="secondary-button min-h-9 px-4" disabled={csvBusy !== null} onClick={() => exportCsv([t.name])}>
              {csvBusy === t.name ? 'Preparo…' : t.name}
            </button>
          ))}
          <button type="button" className="secondary-button min-h-9 px-4" disabled={csvBusy !== null} onClick={() => exportCsv(schema.tables.map((t) => t.name))}>Tutte</button>
        </div>
      )}
      {csvError && <p role="alert" className="text-sm text-red-600">{csvError}</p>}
    </section>
  )
}
