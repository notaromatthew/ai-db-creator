import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { IntervalChart, METRIC_COLORS, METRIC_LABELS, type Row } from './charts'
import FilterBar from './FilterBar'
import { ExportButtons } from './RunsTab'
import { CONDITION_LABEL, NO_FILTERS, filterQuery, fmt, usd, type Filters, type Group, type Meta } from './types'

const label = (g: Group) => `${g.dataset} · ${CONDITION_LABEL[g.condition] ?? g.condition} · ${g.model} · t=${String(g.temperature ?? '—').replace('.', ',')}`
const rowOf = (g: Group, keys: (keyof Pick<Group, 'f1' | 'precision' | 'recall' | 'value_accuracy' | 'judge_score'>)[]): Row => ({
  label: `${label(g)} (n=${g.n_runs})`,
  series: keys.map((k) => ({ key: k, label: METRIC_LABELS[k], color: METRIC_COLORS[k], stat: g[k] })),
})

export default function CompareTab({ meta }: { meta: Meta | null }) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)
  const [groups, setGroups] = useState<Group[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setError('')
    api.get(`/research/summary${filterQuery(filters)}`)
      .then((r) => alive && setGroups(r.groups))
      .catch((e) => alive && setError((e as Error).message))
    return () => { alive = false }
  }, [filters])

  return (
    <div className="flex flex-col gap-6">
      <FilterBar meta={meta} value={filters} onChange={setFilters} />
      <ExportButtons filters={filters} />
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      {groups == null ? <p role="status" className="text-sm text-tecnia-muted">Calcolo i confronti…</p> : (
        <>
          <p className="text-xs text-tecnia-muted">Medie sui run completati, con intervallo di confidenza al 95% (bootstrap). Con una sola ripetizione l'intervallo coincide con la media.</p>
          <IntervalChart title="F1, precisione e richiamo per dataset e condizione" rows={groups.map((g) => rowOf(g, ['f1', 'precision', 'recall']))} />
          <IntervalChart title="F1, accuratezza dei valori e giudice LLM" rows={groups.map((g) => rowOf(g, ['f1', 'value_accuracy', 'judge_score']))} />
          <section aria-label="Costo e latenza">
            <h3 className="mb-2 text-sm font-semibold">Costo e latenza (dai log dei token)</h3>
            {groups.length === 0 ? <p className="text-sm text-tecnia-muted">Nessun dato.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead><tr className="text-xs text-tecnia-muted"><th className="py-1 pr-3">Gruppo</th><th className="pr-3">Costo medio per run</th><th className="pr-3">Costo totale</th><th className="pr-3">Latenza media</th><th>Token medi (ingresso / uscita)</th></tr></thead>
                  <tbody>
                    {groups.map((g) => (
                      <tr key={label(g)} className="border-t border-tecnia-line/50 tabular-nums">
                        <th scope="row" className="py-1 pr-3 font-medium">{label(g)}</th>
                        <td className="pr-3">{usd(g.cost_usd_mean)}</td><td className="pr-3">{usd(g.cost_usd_total)}</td>
                        <td className="pr-3">{g.latency_s_mean == null ? '—' : `${fmt(g.latency_s_mean, 1)} s`}</td>
                        <td>{fmt(g.tokens_in_mean, 0)} / {fmt(g.tokens_out_mean, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
