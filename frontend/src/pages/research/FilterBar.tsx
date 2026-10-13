import type { Filters, Meta } from './types'
import { CONDITION_LABEL } from './types'

const sel = 'rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 text-sm dark:bg-slate-900'

export default function FilterBar({ meta, value, onChange }: { meta: Meta | null; value: Filters; onChange: (f: Filters) => void }) {
  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLSelectElement>) => onChange({ ...value, [k]: e.target.value })
  const o = meta?.filters
  return (
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Filtri">
      <label className="flex flex-col gap-1 text-xs font-semibold">Dataset
        <select className={sel} value={value.dataset} onChange={set('dataset')}>
          <option value="">Tutti</option>
          {(o?.datasets ?? []).map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold">Condizione
        <select className={sel} value={value.condition} onChange={set('condition')}>
          <option value="">Tutte</option>
          {(o?.conditions ?? []).map((c) => <option key={c} value={c}>{CONDITION_LABEL[c] ?? c}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold">Modello
        <select className={sel} value={value.model} onChange={set('model')}>
          <option value="">Tutti</option>
          {(o?.models ?? []).map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs font-semibold">Temperatura
        <select className={sel} value={value.temperature} onChange={set('temperature')}>
          <option value="">Tutte</option>
          {(o?.temperatures ?? []).map((t) => <option key={t} value={String(t)}>{String(t).replace('.', ',')}</option>)}
        </select>
      </label>
    </div>
  )
}
