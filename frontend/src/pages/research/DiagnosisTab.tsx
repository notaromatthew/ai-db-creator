import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { fmt, type Meta } from './types'

interface Diagnosis {
  available: boolean; reason?: string; n_runs: number
  best?: { id: string; run_index: number; f1: number; model: string }[]
  worst?: { id: string; run_index: number; f1: number; model: string }[]
  per_table?: { table: string; f1_best: number | null; f1_worst: number | null; delta: number | null; schema_loss_worst: number | null; population_loss_worst: number | null }[]
  attribution?: { schema_share: number; population_share: number; verdict: string; note: string }
}

const VERDICT: Record<string, string> = {
  schema: 'La perdita dipende soprattutto dallo schema generato.',
  popolamento: 'La perdita dipende soprattutto dal popolamento dei dati.',
  mista: 'La perdita è divisa tra schema e popolamento.',
  'nessuna perdita': 'Nessuna perdita misurabile.',
}

export default function DiagnosisTab({ meta }: { meta: Meta | null }) {
  const [dataset, setDataset] = useState('university')
  const [condition, setCondition] = useState('full_llm')
  const [temperature, setTemperature] = useState('0.5')
  const [data, setData] = useState<Diagnosis | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setData(null); setError('')
    api.get(`/research/diagnosis?dataset=${encodeURIComponent(dataset)}&condition=${encodeURIComponent(condition)}&temperature=${encodeURIComponent(temperature)}`)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError((e as Error).message))
    return () => { alive = false }
  }, [dataset, condition, temperature])

  const sel = 'rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 text-sm dark:bg-slate-900'
  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-2xl text-sm text-tecnia-muted">Confronta, tabella per tabella, i run migliori e peggiori e attribuisce la perdita di F1 allo schema (tabelle e colonne non generate) o al popolamento (valori sbagliati o mancanti).</p>
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold">Dataset
          <select className={sel} value={dataset} onChange={(e) => setDataset(e.target.value)}>{(meta?.datasets ?? ['university']).map((d) => <option key={d}>{d}</option>)}</select></label>
        <label className="flex flex-col gap-1 text-xs font-semibold">Condizione
          <select className={sel} value={condition} onChange={(e) => setCondition(e.target.value)}>{(meta?.conditions ?? ['full_llm']).map((d) => <option key={d}>{d}</option>)}</select></label>
        <label className="flex flex-col gap-1 text-xs font-semibold">Temperatura
          <select className={sel} value={temperature} onChange={(e) => setTemperature(e.target.value)}>{(meta?.temperatures ?? [0.5]).map((t) => <option key={t} value={String(t)}>{String(t).replace('.', ',')}</option>)}</select></label>
      </div>
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      {!data && !error && <p role="status" className="text-sm text-tecnia-muted">Analizzo i run…</p>}
      {data && !data.available && <p className="text-sm text-tecnia-muted">{data.reason}</p>}
      {data?.available && data.attribution && (
        <>
          <section className="glass flex flex-col gap-2 p-5" aria-label="Attribuzione della perdita">
            <h3 className="text-base font-semibold">{VERDICT[data.attribution.verdict] ?? data.attribution.verdict}</h3>
            <div className="flex h-3 max-w-md overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700" role="img" aria-label={`Schema ${fmt(data.attribution.schema_share * 100, 0)} per cento, popolamento ${fmt(data.attribution.population_share * 100, 0)} per cento`}>
              <i className="block h-full" style={{ width: `${data.attribution.schema_share * 100}%`, background: '#8a2be2' }} />
              <i className="block h-full" style={{ width: `${data.attribution.population_share * 100}%`, background: '#e05a00' }} />
            </div>
            <p className="text-xs"><span className="mr-3">Schema: {fmt(data.attribution.schema_share * 100, 0)}%</span><span>Popolamento: {fmt(data.attribution.population_share * 100, 0)}%</span></p>
            <p className="text-xs text-tecnia-muted">{data.attribution.note} Run analizzati: {data.n_runs}.</p>
          </section>
          <div className="grid gap-3 sm:grid-cols-2">
            <section><h4 className="mb-1 text-sm font-semibold">Run migliori</h4><ul className="text-sm">{data.best?.map((r) => <li key={r.id}>#{r.run_index} · F1 {fmt(r.f1)}</li>)}</ul></section>
            <section><h4 className="mb-1 text-sm font-semibold">Run peggiori</h4><ul className="text-sm">{data.worst?.map((r) => <li key={r.id}>#{r.run_index} · F1 {fmt(r.f1)}</li>)}</ul></section>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <caption className="sr-only">Analisi per tabella</caption>
              <thead><tr className="text-xs text-tecnia-muted"><th className="py-1 pr-3">Tabella</th><th className="pr-3">F1 migliori</th><th className="pr-3">F1 peggiori</th><th className="pr-3">Differenza</th><th className="pr-3">Perdita di schema (peggiori)</th><th>Perdita di popolamento (peggiori)</th></tr></thead>
              <tbody>
                {data.per_table?.map((t) => (
                  <tr key={t.table} className="border-t border-tecnia-line/50 tabular-nums">
                    <th scope="row" className="py-1 pr-3 font-medium">{t.table}</th><td className="pr-3">{fmt(t.f1_best)}</td><td className="pr-3">{fmt(t.f1_worst)}</td>
                    <td className="pr-3">{fmt(t.delta)}</td><td className="pr-3">{fmt(t.schema_loss_worst)}</td><td>{fmt(t.population_loss_worst)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
