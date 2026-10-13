import { useState } from 'react'
import { useDialog } from '@/hooks/useDialog'

export const ONBOARDING_STEPS = [
  { icon: 'upload_file', title: 'Parti dai tuoi documenti', text: 'Crea un progetto e carica PDF, fogli Excel, CSV o script SQL. Non serve preparare nulla: l\'IA legge testo e colonne da sola.' },
  { icon: 'schema', title: 'Controlla lo schema', text: 'Vedi tabelle e relazioni in un diagramma. Correggile a mano o chiedi una modifica alla chat. Nulla è definitivo finché non lo confermi.' },
  { icon: 'download', title: 'Scarica o condividi', text: 'Esporta lo script per il database che preferisci, oppure invita colleghi e clienti scegliendo se possono leggere o modificare.' },
] as const

const key = (user: string) => `aidb.onboarding.done.${user}`

export function hasSeenOnboarding(user: string): boolean {
  try { return localStorage.getItem(key(user)) === '1' } catch { return true /* senza storage non insistiamo ad ogni pagina */ }
}
export function markOnboardingSeen(user: string) {
  try { localStorage.setItem(key(user), '1') } catch { /* ignora */ }
}

/** Le tre schermate: usate sia nella finestra di benvenuto sia nella pagina dedicata. */
export function OnboardingSteps({ onFinish, onSkip, finishLabel = 'Inizia' }: { onFinish: () => void; onSkip?: () => void; finishLabel?: string }) {
  const [i, setI] = useState(0)
  const step = ONBOARDING_STEPS[i]
  const last = i === ONBOARDING_STEPS.length - 1
  return (
    <div className="flex flex-col gap-5">
      <p className="text-xs font-bold uppercase tracking-wider text-tecnia-primary" aria-live="polite">Passo {i + 1} di {ONBOARDING_STEPS.length}</p>
      <div className="flex items-start gap-4">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#ff6b00] to-[#fe3ac6] text-white" aria-hidden="true">
          <span className="material-symbols-outlined !text-[28px]">{step.icon}</span>
        </span>
        <div>
          <h3 className="text-xl font-bold">{step.title}</h3>
          <p className="mt-1.5 text-sm leading-6 text-tecnia-muted">{step.text}</p>
        </div>
      </div>
      <div className="flex gap-2" aria-hidden="true">
        {ONBOARDING_STEPS.map((s, n) => <span key={s.title} className={`h-1.5 flex-1 rounded-full ${n <= i ? 'bg-tecnia-orange' : 'bg-tecnia-line'}`} />)}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        {onSkip ? <button type="button" onClick={onSkip} className="rounded-full px-3 py-2 text-sm font-semibold text-tecnia-muted underline">Salta la presentazione</button> : <span />}
        <div className="flex gap-2">
          {i > 0 && <button type="button" onClick={() => setI(i - 1)} className="secondary-button">Indietro</button>}
          <button type="button" data-autofocus onClick={() => (last ? onFinish() : setI(i + 1))} className="primary-button">{last ? finishLabel : 'Avanti'}</button>
        </div>
      </div>
    </div>
  )
}

/** Finestra di benvenuto al primo accesso; si puo' chiudere con Esc, con "Salta" o a fine percorso. */
export function OnboardingDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useDialog<HTMLDivElement>(open, onClose)
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-tecnia-ink/45 p-4">
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="onb-title" className="my-auto w-full max-w-lg rounded-3xl border border-tecnia-line/50 bg-white p-6 shadow-[0_20px_60px_rgba(26,34,51,.3)] sm:p-7 dark:border-slate-700 dark:bg-slate-900">
        <h2 id="onb-title" className="mb-4 text-2xl font-bold tracking-tight">Benvenuto in AI-DB-Creator</h2>
        <OnboardingSteps onFinish={onClose} onSkip={onClose} />
      </div>
    </div>
  )
}
