import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listSchemaVersions, restoreSchemaVersion } from '@/api/projects'
import type { SchemaVersionList } from '@/types'

const ORIGIN: Record<string, string> = {
  generazione: 'Generata dall\'IA',
  chat: 'Modifica dalla chat',
  manuale: 'Modifica a mano',
  ripristino: 'Ripristino',
}

const formatDate = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
}

interface Props {
  projectId: string
  readOnly?: boolean
}

/** Cronologia delle versioni dello schema, con ripristino. */
export default function SchemaVersionsPanel({ projectId, readOnly = false }: Props) {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null)
  const { data, isError } = useQuery<SchemaVersionList>({
    queryKey: ['schema-versions', projectId],
    queryFn: () => listSchemaVersions(projectId),
    retry: false,
  })

  const restore = useMutation({
    mutationFn: (version: number) => restoreSchemaVersion(projectId, version),
    onSuccess: (res) => {
      setMessage({ text: `Ho ripristinato la versione ${res.restored_from}: ora sei alla versione ${res.schema_version}.`, error: false })
      for (const key of ['schema', 'schema-versions', 'project', 'stats']) queryClient.invalidateQueries({ queryKey: [key, projectId] })
    },
    onError: (e: any) => setMessage({ text: e?.message || 'Non è stato possibile ripristinare questa versione.', error: true }),
  })

  const onRestore = (version: number) => {
    if (!window.confirm(`Ripristinare la versione ${version}? Lo schema attuale viene sostituito, ma resta salvato nella cronologia.`)) return
    setMessage(null)
    restore.mutate(version)
  }

  const versions = data?.versions ?? []
  const locked = readOnly || !!data?.finalized

  return (
    <details className="surface p-4">
      <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold">
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">history</span>
        Cronologia delle versioni{data ? ` (${versions.length})` : ''}
      </summary>
      <div className="mt-3 space-y-2">
        {isError && <p role="alert" className="text-sm text-red-600">Non riesco a caricare la cronologia.</p>}
        {data?.finalized && <p className="text-xs text-tecnia-muted dark:text-slate-400">Lo schema è definitivo: le versioni si possono solo consultare.</p>}
        {versions.length === 0 && data && <p className="text-sm text-tecnia-muted dark:text-slate-400">Nessuna versione salvata per ora.</p>}
        <ul className="space-y-2">
          {versions.map((v) => {
            const current = v.version === data?.current
            return (
              <li key={v.version} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-tecnia-line/60 px-3 py-2 text-sm dark:border-slate-700">
                <span className="min-w-0">
                  <b className="font-headline">Versione {v.version}</b>{current && <span className="tag ml-2">Attuale</span>}
                  <span className="block text-xs text-tecnia-muted dark:text-slate-400">
                    {ORIGIN[v.origin] ?? v.origin}{v.author_label ? ` · ${v.author_label}` : ''}{formatDate(v.created_at) ? ` · ${formatDate(v.created_at)}` : ''}
                    {typeof v.table_count === 'number' ? ` · ${v.table_count} ${v.table_count === 1 ? 'tabella' : 'tabelle'}` : ''}
                  </span>
                </span>
                {!current && (
                  <button type="button" className="secondary-button min-h-9 px-4" disabled={locked || restore.isPending} onClick={() => onRestore(v.version)} aria-label={`Ripristina la versione ${v.version}`}>
                    Ripristina
                  </button>
                )}
              </li>
            )
          })}
        </ul>
        <p role={message?.error ? 'alert' : 'status'} aria-live="polite" className={`text-sm ${message?.error ? 'text-red-600' : 'text-emerald-700 dark:text-emerald-300'}`}>{message?.text}</p>
      </div>
    </details>
  )
}
