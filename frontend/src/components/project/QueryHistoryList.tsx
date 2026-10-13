import { useQuery } from '@tanstack/react-query'
import { listQueries } from '@/api/projects'
import type { QueryHistoryItem } from '@/types'

interface Props {
  projectId: string
  onPick: (item: QueryHistoryItem) => void
}

const formatDate = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
}

/** Ultime domande e query del progetto: un clic le riporta nel campo di ricerca. */
export default function QueryHistoryList({ projectId, onPick }: Props) {
  const { data = [], isError } = useQuery<QueryHistoryItem[]>({
    queryKey: ['queries', projectId],
    queryFn: () => listQueries(projectId),
    retry: false,
  })
  if (isError) return <p role="alert" className="text-sm text-red-600">Non riesco a caricare le domande precedenti.</p>
  if (data.length === 0) return null
  return (
    <section className="surface p-4" aria-label="Domande precedenti">
      <h3 className="mb-2 flex items-center gap-2 font-headline text-sm font-bold">
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">history</span>Domande precedenti
      </h3>
      <ul className="max-h-60 space-y-1 overflow-auto">
        {data.map((q) => {
          const text = q.question || q.sql || ''
          const failed = q.outcome && q.outcome !== 'ok' && q.outcome !== 'success'
          return (
            <li key={q.id}>
              <button type="button" onClick={() => onPick(q)} className="flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-orange-500/10">
                <span className="material-symbols-outlined mt-0.5 text-[18px]" aria-hidden="true">{q.source === 'execute' ? 'terminal' : 'chat'}</span>
                <span className="min-w-0 flex-1">
                  <span className={`block truncate ${q.source === 'execute' && !q.question ? 'font-mono text-xs' : ''}`}>{text}</span>
                  <span className="block text-xs text-tecnia-muted dark:text-slate-400">
                    {formatDate(q.created_at)}{typeof q.rows === 'number' ? ` · ${q.rows} righe` : ''}{failed ? ' · non riuscita' : ''}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
