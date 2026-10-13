import type { ReactNode } from 'react'

export interface BarAction {
  label: string
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  icon?: string
}

interface Props {
  step: number
  total?: number
  /** Testo di contesto accanto al numero del passo. */
  info?: ReactNode
  /** Avviso mostrato quando i controlli sono bloccati (es. sola lettura). */
  note?: string
  back?: BarAction
  secondary?: BarAction
  primary?: BarAction
}

function Content({ action }: { action: BarAction }) {
  return (
    <>
      {action.loading && <span className="material-symbols-outlined animate-spin text-[18px]" aria-hidden="true">progress_activity</span>}
      {action.label}
      {!action.loading && action.icon && <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{action.icon}</span>}
    </>
  )
}

export default function ActionBar({ step, total = 4, info, note, back, secondary, primary }: Props) {
  return (
    <div
      role="region"
      aria-label="Azioni del passo"
      className="sticky bottom-0 z-30 -mx-4 mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-tecnia-line bg-white/95 px-4 py-3 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 sm:mx-0 sm:rounded-t-2xl"
    >
      <div className="min-w-0 flex-1 text-sm text-tecnia-muted dark:text-slate-400">
        <b className="font-headline text-tecnia-ink dark:text-slate-100">Passo {step} di {total}</b>
        {info && <> · {info}</>}
        {note && <p className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-amber-700 dark:text-amber-300"><span className="material-symbols-outlined text-[16px]" aria-hidden="true">visibility</span>{note}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {back && (
          <button type="button" className="secondary-button" onClick={back.onClick} disabled={back.disabled}>
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">arrow_back</span>{back.label}
          </button>
        )}
        {secondary && (
          <button type="button" className="secondary-button" onClick={secondary.onClick} disabled={secondary.disabled || secondary.loading}>
            <Content action={secondary} />
          </button>
        )}
        {primary && (
          <button type="button" className="primary-button" onClick={primary.onClick} disabled={primary.disabled || primary.loading}>
            <Content action={primary} />
          </button>
        )}
      </div>
    </div>
  )
}
