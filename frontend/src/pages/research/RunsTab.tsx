import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import FilterBar from './FilterBar'
import {
  CONDITION_LABEL, STATUS_LABEL, NO_FILTERS, downloadText, filterQuery, fmt, usd,
  type Filters, type Meta, type RunDetail, type RunRow,
} from './types'

function Ico({ n }: { n: string }) {
  return <span aria-hidden="true" className="material-symbols-outlined !text-[18px] align-middle">{n}</span>
}

export function RunDetailView({ run, onClose }: { run: RunDetail; onClose: () => void }) {
  const tables = run.schema?.tables ?? []
  const perTable = Object.entries(run.per_table ?? {})
  return (
    <section className="glass flex flex-col gap-4 p-5" aria-label="Dettaglio del run">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">{run.dataset} · {CONDITION_LABEL[run.condition] ?? run.condition} · ripetizione {run.run_index}</h3>
        <button type="button" className="secondary-button !min-h-9" onClick={onClose}><Ico n="close" /> Chiudi</button>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <div><dt className="text-xs text-tecnia-muted">F1</dt><dd className="tabular-nums">{fmt(run.f1)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Precisione</dt><dd className="tabular-nums">{fmt(run.precision)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Richiamo</dt><dd className="tabular-nums">{fmt(run.recall)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Accuratezza valori</dt><dd className="tabular-nums">{fmt(run.value_accuracy)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Giudice LLM</dt><dd className="tabular-nums">{fmt(run.judge_score)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Costo</dt><dd className="tabular-nums">{usd(run.cost_usd)}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Latenza</dt><dd className="tabular-nums">{run.latency_s == null ? '—' : `${fmt(run.latency_s, 1)} s`}</dd></div>
        <div><dt className="text-xs text-tecnia-muted">Token (ingresso / uscita)</dt><dd className="tabular-nums">{run.tokens_in ?? '—'} / {run.tokens_out ?? '—'}</dd></div>
      </dl>
      {run.error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{run.error}</p>}
      <div>
        <h4 className="mb-1 text-sm font-semibold">Schema generato</h4>
        {tables.length === 0 ? <p className="text-sm text-tecnia-muted">Nessuno schema registrato per questo run.</p> : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {tables.map((t) => (
              <li key={t.name} className="rounded-xl border border-tecnia-line/60 p-3 text-sm">
                <strong>{t.name}</strong>
                <div className="mt-1 text-xs text-tecnia-muted">{(t.columns ?? []).map((c) => c.name).join(', ')}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
      {perTable.length > 0 && (
        <div className="overflow-x-auto">
          <h4 className="mb-1 text-sm font-semibold">Metriche per tabella</h4>
          <table className="w-full text-left text-sm">
            <thead><tr><th className="py-1 pr-3">Tabella</th><th className="pr-3">F1</th><th className="pr-3">Precisione</th><th className="pr-3">Richiamo</th><th>Celle</th></tr></thead>
            <tbody>
              {perTable.map(([name, m]) => (
                <tr key={name} className="border-t border-tecnia-line/50 tabular-nums">
                  <th scope="row" className="py-1 pr-3 font-medium">{name}</th><td className="pr-3">{fmt(m.f1)}</td><td className="pr-3">{fmt(m.precision)}</td><td className="pr-3">{fmt(m.recall)}</td><td>{m.total_cells}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div>
        <h4 className="mb-1 text-sm font-semibold">Manifesto di riproducibilità</h4>
        <pre className="max-h-72 overflow-auto rounded-xl bg-slate-100 p-3 text-xs dark:bg-slate-900">{JSON.stringify(run.manifest ?? {}, null, 2)}</pre>
      </div>
    </section>
  )
}

export function ExportButtons({ filters }: { filters: Filters }) {
  const [error, setError] = useState('')
  const go = async (format: 'csv' | 'json') => {
    setError('')
    try {
      const r = await api.get(`/research/export${filterQuery(filters, { format, wrap: '1' })}`)
      downloadText(r.filename, r.mime, r.content)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" className="secondary-button !min-h-9" onClick={() => go('csv')}><Ico n="download" /> Esporta CSV</button>
      <button type="button" className="secondary-button !min-h-9" onClick={() => go('json')}><Ico n="download" /> Esporta JSON</button>
      {error && <span role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</span>}
    </div>
  )
}

export default function RunsTab({ meta }: { meta: Meta | null }) {
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      setRuns((await api.get(`/research/runs${filterQuery(filters)}`)).runs)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [filters])
  useEffect(() => { load() }, [load])

  const open = async (id: string) => {
    try { setDetail(await api.get(`/research/runs/${id}`)) } catch (e) { setError((e as Error).message) }
  }

  return (
    <div className="flex flex-col gap-4">
      <FilterBar meta={meta} value={filters} onChange={setFilters} />
      <ExportButtons filters={filters} />
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      {runs == null ? <p role="status" className="text-sm text-tecnia-muted">Carico i run…</p> : runs.length === 0 ? (
        <p className="text-sm text-tecnia-muted">Nessun run con questi filtri. Avviane uno dalla scheda "Lancio".</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <caption className="sr-only">Run di benchmark</caption>
            <thead>
              <tr className="text-xs text-tecnia-muted">
                <th className="py-2 pr-3">Dataset</th><th className="pr-3">Condizione</th><th className="pr-3">Modello</th><th className="pr-3">Temp.</th>
                <th className="pr-3">Stato</th><th className="pr-3">F1</th><th className="pr-3">Valori</th><th className="pr-3">Costo</th><th className="pr-3">Latenza</th><th><span className="sr-only">Azioni</span></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-tecnia-line/50 tabular-nums">
                  <td className="py-2 pr-3">{r.dataset}</td><td className="pr-3">{CONDITION_LABEL[r.condition] ?? r.condition}</td>
                  <td className="pr-3">{r.model}</td><td className="pr-3">{r.temperature == null ? '—' : String(r.temperature).replace('.', ',')}</td>
                  <td className="pr-3">{STATUS_LABEL[r.status] ?? r.status}</td><td className="pr-3">{fmt(r.f1)}</td><td className="pr-3">{fmt(r.value_accuracy)}</td>
                  <td className="pr-3">{usd(r.cost_usd)}</td><td className="pr-3">{r.latency_s == null ? '—' : `${fmt(r.latency_s, 1)} s`}</td>
                  <td><button type="button" className="text-tecnia-magentaDeep underline dark:text-pink-300" onClick={() => open(r.id)} aria-label={`Dettaglio del run ${r.dataset} ${r.run_index}`}>Dettaglio</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {detail && <RunDetailView run={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}
