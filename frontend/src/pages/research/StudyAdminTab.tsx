import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { downloadText } from './types'

interface Arm { arm: string; enrolled: number; active: number; completed: number; withdrawn: number; target: number }
interface Status { arms: Arm[]; total: number; balanced: boolean; consent_version: string }

const ARM_LABEL: Record<string, string> = { manual: 'Manuale (senza IA)', ai_only: 'Solo IA', ai_interface: 'IA con interfaccia' }

export default function StudyAdminTab() {
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [code, setCode] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try { setStatus(await api.get('/study/admin/status')); setError('') } catch (e) { setError((e as Error).message) }
  }, [])
  useEffect(() => { load() }, [load])

  const exportKind = async (kind: string) => {
    try {
      const r = await api.get(`/study/admin/export?kind=${kind}&wrap=1`)
      downloadText(r.filename, r.mime, r.content)
    } catch (e) { setError((e as Error).message) }
  }

  const erase = async () => {
    setMessage(''); setError('')
    if (!window.confirm('Cancellare in modo definitivo i dati di questa persona? L\'operazione non si può annullare.')) return
    try {
      await api.post('/study/admin/erase', { code })
      setMessage('Dati cancellati. Restano solo il braccio assegnato e la data di ritiro, senza altri dati.')
      setCode('')
      load()
    } catch (e) { setError((e as Error).message) }
  }

  return (
    <div className="flex flex-col gap-6">
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      <section aria-labelledby="arms-h" className="flex flex-col gap-2">
        <h3 id="arms-h" className="text-base font-semibold">Stato dei bracci</h3>
        {!status ? <p role="status" className="text-sm text-tecnia-muted">Carico lo stato…</p> : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead><tr className="text-xs text-tecnia-muted"><th className="py-1 pr-3">Braccio</th><th className="pr-3">Attivi</th><th className="pr-3">Completati</th><th className="pr-3">Ritirati</th><th>Obiettivo</th></tr></thead>
                <tbody>
                  {status.arms.map((a) => (
                    <tr key={a.arm} className="border-t border-tecnia-line/50 tabular-nums">
                      <th scope="row" className="py-1 pr-3 font-medium">{ARM_LABEL[a.arm] ?? a.arm}</th><td className="pr-3">{a.active}</td><td className="pr-3">{a.completed}</td><td className="pr-3">{a.withdrawn}</td><td>{a.target}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-tecnia-muted" role="status">Iscritti in totale: {status.total}. {status.balanced ? 'I bracci sono bilanciati.' : 'I bracci non sono bilanciati: le prossime assegnazioni compensano.'} Versione dell'informativa: {status.consent_version}.</p>
          </>
        )}
      </section>
      <section aria-labelledby="exp-h" className="flex flex-col gap-2">
        <h3 id="exp-h" className="text-base font-semibold">Esportazione dei dati (CSV)</h3>
        <p className="text-xs text-tecnia-muted">Gli id sono pseudonimi casuali: nessuna email, nessun indirizzo IP, nessun collegamento con gli account.</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="secondary-button !min-h-9" onClick={() => exportKind('participants')}>Partecipanti</button>
          <button type="button" className="secondary-button !min-h-9" onClick={() => exportKind('responses')}>Risposte</button>
          <button type="button" className="secondary-button !min-h-9" onClick={() => exportKind('events')}>Eventi</button>
        </div>
      </section>
      <section aria-labelledby="erase-h" className="glass flex flex-col gap-2 p-5">
        <h3 id="erase-h" className="text-base font-semibold">Cancellazione su richiesta</h3>
        <p className="text-xs text-tecnia-muted">Chi ha partecipato può chiedere la cancellazione comunicandoti il suo codice di ritiro.</p>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-xs font-semibold">Codice del partecipante
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="XXXXX-XXXXX" autoComplete="off" className="rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 text-sm font-normal uppercase dark:bg-slate-900" />
          </label>
          <button type="button" className="secondary-button" disabled={code.trim().length < 5} onClick={erase}>Cancella i dati</button>
        </div>
        {message && <p role="status" className="text-sm text-tecnia-ok">{message}</p>}
      </section>
    </div>
  )
}
