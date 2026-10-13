import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

/** Avanzamento stimato (la generazione e' una sola chiamata, senza stato intermedio): sale piano verso il 92%. */
export function useSimulatedProgress(active: boolean, startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [active])
  if (!active || !startedAt) return 0
  const seconds = Math.max(0, (now - startedAt) / 1000)
  return Math.round(92 * (1 - Math.exp(-seconds / 45)))
}

const ITEMS = [
  { until: 12, label: 'Documenti letti' },
  { until: 40, label: 'Tabelle individuate' },
  { until: 70, label: 'Controllo relazioni e tipi' },
  { until: 101, label: 'Preparo la proposta da rivedere' },
]

interface Props {
  progress: number
  error?: string
  onRetry?: () => void
}

export default function GenerationProgress({ progress, error, onRetry }: Props) {
  const activeIndex = ITEMS.findIndex((item) => progress < item.until)
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 py-6">
      <div className="glass flex flex-col gap-5 p-6 sm:p-8">
        <div className="flex items-center gap-4">
          <span className="material-symbols-outlined text-[34px] text-tecnia-primary dark:text-orange-300" aria-hidden="true">auto_awesome</span>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{error ? 'Non sono riuscito a generare lo schema' : 'Sto leggendo i tuoi documenti'}</h2>
            <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">{error || 'Di solito servono meno di due minuti.'}</p>
          </div>
        </div>
        {error ? (
          onRetry && <button type="button" className="primary-button w-fit" onClick={onRetry}>Riprova</button>
        ) : (
          <>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Avanzamento">
              <div className="h-full rounded-full bg-gradient-to-r from-orange-500 to-fuchsia-500 transition-all duration-700" style={{ width: `${progress}%` }} />
            </div>
            <ul>
              {ITEMS.map((item, i) => {
                const done = i < activeIndex
                const current = i === activeIndex
                return (
                  <li key={item.label} className={`flex items-center gap-3 py-2.5 text-[15px] ${!done && !current ? 'text-tecnia-muted dark:text-slate-500' : ''}`}>
                    <span
                      className={`material-symbols-outlined ${done ? 'text-tecnia-ok' : current ? 'animate-spin text-tecnia-primary' : ''}`}
                      aria-hidden="true"
                    >
                      {done ? 'check_circle' : current ? 'progress_activity' : 'radio_button_unchecked'}
                    </span>
                    <span className={current ? 'font-headline font-bold' : ''}>{item.label}</span>
                  </li>
                )
              })}
            </ul>
          </>
        )}
      </div>
      <div className="glass flex flex-wrap items-center gap-4 p-5">
        <span className="material-symbols-outlined text-fuchsia-700" aria-hidden="true">info</span>
        <p className="min-w-[220px] flex-1 text-sm leading-6">Puoi chiudere la pagina: il lavoro continua e lo ritrovi qui, nel tuo elenco progetti, con lo stato aggiornato.</p>
        <Link to="/app" className="secondary-button">Torna ai progetti</Link>
      </div>
    </div>
  )
}
