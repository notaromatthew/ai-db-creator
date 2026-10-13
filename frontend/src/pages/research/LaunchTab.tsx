import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { CONDITION_LABEL, STATUS_LABEL, fmt, usd, type Meta, type RunRow } from './types'

interface Estimate { runs: number; tokens_in: number; tokens_out: number; cost_usd: number; cap_usd: number; over_cap: boolean }
interface Queue { active: RunRow[]; recent: RunRow[]; queued: number; running: number }

const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v])

export function QueuePanel({ onChange }: { onChange?: () => void }) {
  const [queue, setQueue] = useState<Queue | null>(null)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    try { setQueue(await api.get('/research/queue')); setError('') } catch (e) { setError((e as Error).message) }
  }, [])
  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load])
  const cancel = async (id: string) => {
    try { await api.post(`/research/runs/${id}/cancel`, {}); await load(); onChange?.() } catch (e) { setError((e as Error).message) }
  }
  const list = [...(queue?.active ?? [])]
  return (
    <section className="glass flex flex-col gap-3 p-5" aria-labelledby="queue-h">
      <h3 id="queue-h" className="text-base font-semibold">Coda dei lavori</h3>
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      {queue == null ? <p role="status" className="text-sm text-tecnia-muted">Carico la coda…</p> : list.length === 0 ? (
        <p className="text-sm text-tecnia-muted">Nessun lavoro in coda o in corso.</p>
      ) : (
        <>
          <p className="text-xs text-tecnia-muted" role="status">{queue.running} in corso, {queue.queued} in attesa.</p>
          <ul className="flex flex-col gap-1.5">
            {list.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-tecnia-line/60 px-3 py-2 text-sm">
                <span>{r.dataset} · {CONDITION_LABEL[r.condition] ?? r.condition} · t={String(r.temperature).replace('.', ',')} · #{r.run_index}
                  <span className="tag ml-2">{r.cancel_requested ? 'Annullamento richiesto' : STATUS_LABEL[r.status] ?? r.status}</span></span>
                <button type="button" className="secondary-button !min-h-8 !px-3" disabled={r.cancel_requested} onClick={() => cancel(r.id)} aria-label={`Annulla il run ${r.dataset} ${r.run_index}`}>Annulla</button>
              </li>
            ))}
          </ul>
        </>
      )}
      {queue && queue.recent.length > 0 && (
        <details className="text-xs"><summary className="cursor-pointer text-tecnia-muted">Ultimi conclusi</summary>
          <ul className="mt-1 list-disc pl-5">{queue.recent.map((r) => <li key={r.id}>{r.dataset} · {r.condition} · #{r.run_index}: {STATUS_LABEL[r.status] ?? r.status}</li>)}</ul>
        </details>
      )}
    </section>
  )
}

export default function LaunchTab({ meta, onLaunched }: { meta: Meta | null; onLaunched: () => void }) {
  const [datasets, setDatasets] = useState<string[]>([])
  const [conditions, setConditions] = useState<string[]>(['full_llm'])
  const [temperatures, setTemperatures] = useState<number[]>([0.5])
  const [model, setModel] = useState('')
  const [runs, setRuns] = useState(3)
  const [estimate, setEstimate] = useState<Estimate | null>(null)
  const [error, setError] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [sent, setSent] = useState('')

  useEffect(() => {
    if (!meta) return
    setDatasets((d) => (d.length ? d : meta.datasets.slice(0, 1)))
    setModel((m) => m || meta.models.find((x) => x.current)?.model || meta.models[0]?.model || '')
  }, [meta])

  const ready = datasets.length > 0 && conditions.length > 0 && temperatures.length > 0 && !!model && runs >= 1
  useEffect(() => {
    setConfirmed(false)
    setEstimate(null)
    if (!ready) return
    let alive = true
    setError('')
    api.post('/research/estimate', { datasets, conditions, model, temperatures, runs })
      .then((e) => alive && setEstimate(e))
      .catch((e) => alive && setError((e as Error).message))
    return () => { alive = false }
  }, [datasets, conditions, temperatures, model, runs, ready])

  const launch = async () => {
    setError(''); setSent('')
    try {
      const r = await api.post('/research/batches', { datasets, conditions, model, temperatures, runs, confirm_cost: true })
      setSent(`Messi in coda ${r.runs} run.`)
      setConfirmed(false)
      onLaunched()
    } catch (e) { setError((e as Error).message) }
  }

  if (!meta) return <p role="status" className="text-sm text-tecnia-muted">Carico le opzioni…</p>
  return (
    <div className="flex flex-col gap-5">
      <form className="glass flex flex-col gap-4 p-5" onSubmit={(e) => { e.preventDefault(); if (confirmed && estimate && !estimate.over_cap) launch() }}>
        <fieldset className="flex flex-wrap gap-x-5 gap-y-2"><legend className="mb-1 text-sm font-semibold">Dataset</legend>
          {meta.datasets.map((d) => <label key={d} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={datasets.includes(d)} onChange={() => setDatasets(toggle(datasets, d))} />{d}</label>)}
        </fieldset>
        <fieldset className="flex flex-wrap gap-x-5 gap-y-2"><legend className="mb-1 text-sm font-semibold">Condizione</legend>
          {meta.conditions.map((c) => <label key={c} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={conditions.includes(c)} onChange={() => setConditions(toggle(conditions, c))} />{CONDITION_LABEL[c] ?? c}</label>)}
        </fieldset>
        <fieldset className="flex flex-wrap gap-x-5 gap-y-2"><legend className="mb-1 text-sm font-semibold">Temperatura</legend>
          {meta.temperatures.map((t) => <label key={t} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={temperatures.includes(t)} onChange={() => setTemperatures(toggle(temperatures, t))} />{String(t).replace('.', ',')}</label>)}
        </fieldset>
        <div className="flex flex-wrap gap-4">
          <label className="flex flex-col gap-1 text-sm font-semibold">Modello
            <select className="rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 text-sm font-normal dark:bg-slate-900" value={model} onChange={(e) => setModel(e.target.value)}>
              {meta.models.map((m) => <option key={m.model} value={m.model}>{m.model}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-semibold">Ripetizioni per combinazione
            <input type="number" min={1} max={20} value={runs} onChange={(e) => setRuns(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} className="w-28 rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 text-sm font-normal dark:bg-slate-900" />
          </label>
        </div>

        <div aria-live="polite" className="rounded-xl bg-orange-50 p-4 text-sm dark:bg-slate-800">
          {!ready ? 'Scegli almeno un dataset, una condizione e una temperatura.' : estimate == null ? (error ? '' : 'Calcolo la stima…') : (
            <>
              <p className="font-semibold">Stima prima dell'avvio: {estimate.runs} run, circa {usd(estimate.cost_usd)}</p>
              <p className="text-xs text-tecnia-muted">Token stimati: {fmt(estimate.tokens_in, 0)} in ingresso, {fmt(estimate.tokens_out, 0)} in uscita. Tetto per lancio: {usd(estimate.cap_usd)}. È una stima grezza, non un costo garantito.</p>
              {estimate.over_cap && <p role="alert" className="mt-1 font-semibold text-red-700 dark:text-red-300">La stima supera il tetto: riduci run, dataset o ripetizioni.</p>}
            </>
          )}
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5" checked={confirmed} disabled={!estimate || estimate.over_cap} onChange={(e) => setConfirmed(e.target.checked)} />
          Ho letto la stima del costo e voglio avviare questi run.
        </label>
        {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
        {sent && <p role="status" className="text-sm text-tecnia-ok">{sent}</p>}
        <div><button type="submit" className="primary-button" disabled={!confirmed || !estimate || estimate.over_cap}>Avvia i run</button></div>
      </form>
      <QueuePanel onChange={onLaunched} />
    </div>
  )
}
