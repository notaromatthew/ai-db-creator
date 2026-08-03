import { useState } from 'react'

interface Props {
  documentsCount: number
  hasSchema: boolean
  hasData: boolean
  onGoTo: (tab: string) => void
}

export default function GuidedWorkflow({ documentsCount, hasSchema, hasData, onGoTo }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const steps = [
    { id: 1, label: 'Carica documenti', description: 'carica i file da cui partire', done: documentsCount > 0, active: documentsCount === 0, enabled: true },
    { id: 2, label: 'Genera schema', description: 'crea la struttura del database', done: hasSchema, active: documentsCount > 0 && !hasSchema, enabled: documentsCount > 0 },
    { id: 3, label: 'Popola dati', description: 'inserisci i dati nelle tabelle', done: hasData, active: hasSchema && !hasData, enabled: hasSchema },
    { id: 4, label: 'Esplora', description: 'naviga, cerca ed esporta i dati', done: hasData, active: hasData, enabled: hasData },
  ]
  const current = steps.find((step) => step.active) || steps[steps.length - 1]

  if (collapsed) {
    return (
      <button onClick={() => setCollapsed(false)} className="mb-4 w-full rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm font-semibold text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300">
        Passo {current.id} di 4: {current.label} <span aria-hidden="true">→</span>
      </button>
    )
  }

  return (
    <section className="surface mb-6 p-4 sm:p-5" aria-labelledby="workflow-title">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Il tuo percorso</p>
          <h2 id="workflow-title" className="mt-1 font-bold">Procedura guidata</h2>
        </div>
        <button onClick={() => setCollapsed(true)} className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Riduci procedura guidata">Riduci</button>
      </div>
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {steps.map((step) => (
          <li key={step.id}>
            <button
              onClick={() => step.enabled && onGoTo(step.id <= 2 ? 'schema' : 'data')}
              disabled={!step.enabled}
              className={`flex w-full items-center gap-2 rounded-xl border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${step.done ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30' : step.active ? 'border-blue-300 bg-blue-50 ring-2 ring-blue-100 dark:border-blue-700 dark:bg-blue-950/30 dark:ring-blue-950' : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/60'}`}
              aria-current={step.active ? 'step' : undefined}
              title={!step.enabled ? 'Completa prima il passaggio precedente' : undefined}
            >
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold ${step.done ? 'bg-emerald-600 text-white' : step.active ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-300'}`}>{step.done ? '✓' : step.id}</span>
              <span className={`text-xs font-semibold ${step.active ? 'text-blue-700 dark:text-blue-300' : step.done ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-500 dark:text-slate-400'}`}>{step.label}</span>
            </button>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-sm text-slate-600 dark:text-slate-400"><span className="font-semibold text-slate-800 dark:text-slate-200">Prossima azione: </span>{current.description}.</p>
    </section>
  )
}
