import type { Job } from '@/types'

interface Props {
  job: Job
  title: string
  onCancel?: () => void
  cancelling?: boolean
}

const statusText = (job: Job) => (job.status === 'queued' ? 'In attesa di partire' : 'In corso')

/** Barra di avanzamento di un lavoro in coda, con annuncio per gli screen reader. */
export default function JobProgress({ job, title, onCancel, cancelling }: Props) {
  const value = Math.min(100, Math.max(0, Math.round(job.progress ?? 0)))
  return (
    <section className="glass flex flex-col gap-3 p-5" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-headline text-lg font-bold">{title}</h3>
        {onCancel && (
          <button type="button" className="secondary-button min-h-9 px-4" onClick={onCancel} disabled={cancelling}>
            {cancelling ? 'Annullo…' : 'Annulla'}
          </button>
        )}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={title}>
        <div className="h-full rounded-full bg-gradient-to-r from-orange-500 to-fuchsia-500 transition-all duration-700" style={{ width: `${value}%` }} />
      </div>
      <p className="text-sm text-tecnia-muted dark:text-slate-400" role="status" aria-live="polite">{statusText(job)}: {value}%</p>
    </section>
  )
}
