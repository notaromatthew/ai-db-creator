export const STEPS = [
  { id: 1, label: 'Documenti', icon: 'upload_file' },
  { id: 2, label: 'Schema', icon: 'edit_note' },
  { id: 3, label: 'Database', icon: 'database' },
  { id: 4, label: 'Dati', icon: 'table_chart' },
] as const

interface Props {
  /** Passo mostrato (1-4). */
  current: number
  /** Ultimo passo raggiungibile con lo stato attuale del progetto. */
  reachable: number
  onSelect: (step: number) => void
}

export default function Stepper({ current, reachable, onSelect }: Props) {
  return (
    <nav aria-label="Avanzamento" className="mb-6 flex flex-wrap gap-2">
      {STEPS.map((step) => {
        const done = step.id < current
        const on = step.id === current
        const enabled = step.id <= reachable
        const tone = on
          ? 'border-orange-500 bg-orange-500/10 text-tecnia-primary dark:text-orange-300'
          : done
            ? 'border-tecnia-ok text-tecnia-ok dark:border-emerald-400 dark:text-emerald-300'
            : 'border-tecnia-line text-tecnia-muted dark:border-slate-600 dark:text-slate-400'
        return (
          <button
            key={step.id}
            type="button"
            onClick={() => enabled && onSelect(step.id)}
            disabled={!enabled}
            aria-current={on ? 'step' : undefined}
            title={enabled ? undefined : 'Completa prima il passo precedente'}
            className={`flex min-h-10 items-center gap-2 rounded-full border px-4 py-2 font-headline text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${tone}`}
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{done ? 'check_circle' : step.icon}</span>
            <span>{step.label}</span>
            {done && <span className="sr-only">(completato)</span>}
          </button>
        )
      })}
    </nav>
  )
}
