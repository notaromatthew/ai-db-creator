import type { Stat } from './types'
import { fmt } from './types'

export interface Series { key: string; label: string; color: string; stat: Stat }
export interface Row { label: string; series: Series[] }

export const METRIC_COLORS: Record<string, string> = {
  f1: '#e05a00', precision: '#0b7bb5', recall: '#168a45', value_accuracy: '#8a2be2', judge_score: '#5b6472',
}
export const METRIC_LABELS: Record<string, string> = {
  f1: 'F1', precision: 'Precisione', recall: 'Richiamo', value_accuracy: 'Accuratezza valori', judge_score: 'Giudice LLM',
}

const W = 640
const LEFT = 220
const RIGHT = 24
const LINE = 20
const x = (v: number) => LEFT + Math.max(0, Math.min(1, v)) * (W - LEFT - RIGHT)

/**
 * Grafico a intervalli in SVG: un gruppo per riga, una linea per metrica con punto sulla media e barra
 * dall'estremo basso a quello alto dell'intervallo di confidenza (bootstrap al 95%). Sotto, i valori in tabella.
 */
export function IntervalChart({ title, rows }: { title: string; rows: Row[] }) {
  if (rows.length === 0) return <p className="text-sm text-tecnia-muted">Nessun dato da mostrare con questi filtri.</p>
  const legend = rows[0].series
  const bandH = (n: number) => n * LINE + 18
  let y = 28
  const placed = rows.map((r) => {
    const top = y
    y += bandH(r.series.length)
    return { r, top }
  })
  const height = y + 24
  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="text-sm font-semibold">{title}</figcaption>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Legenda">
        {legend.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />{s.label}
          </li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={title} className="w-full max-w-3xl text-tecnia-ink dark:text-slate-100">
        <title>{title}</title>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={18} y2={height - 24} stroke="currentColor" strokeOpacity={0.12} />
            <text x={x(t)} y={height - 8} fontSize="11" textAnchor="middle" fill="currentColor" fillOpacity={0.7}>{String(t).replace('.', ',')}</text>
          </g>
        ))}
        {placed.map(({ r, top }) => (
          <g key={r.label}>
            <text x={LEFT - 10} y={top + 12} fontSize="12" textAnchor="end" fill="currentColor">{r.label}</text>
            {r.series.map((s, i) => {
              const cy = top + 8 + i * LINE
              const { mean, low, high } = s.stat
              if (mean == null) return null
              return (
                <g key={s.key}>
                  {low != null && high != null && (
                    <>
                      <line x1={x(low)} x2={x(high)} y1={cy} y2={cy} stroke={s.color} strokeWidth={3} strokeLinecap="round" strokeOpacity={0.55} />
                      <line x1={x(low)} x2={x(low)} y1={cy - 4} y2={cy + 4} stroke={s.color} strokeWidth={1.5} />
                      <line x1={x(high)} x2={x(high)} y1={cy - 4} y2={cy + 4} stroke={s.color} strokeWidth={1.5} />
                    </>
                  )}
                  <circle cx={x(mean)} cy={cy} r={4.5} fill={s.color} stroke="#fff" strokeWidth={1} />
                </g>
              )
            })}
          </g>
        ))}
      </svg>
      <details className="text-xs">
        <summary className="cursor-pointer text-tecnia-muted">Mostra i valori in tabella</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <thead><tr><th className="py-1 pr-3">Gruppo</th>{legend.map((s) => <th key={s.key} className="py-1 pr-3">{s.label} (media, intervallo)</th>)}</tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="border-t border-tecnia-line/50">
                  <th scope="row" className="py-1 pr-3 font-medium">{r.label}</th>
                  {r.series.map((s) => (
                    <td key={s.key} className="py-1 pr-3 tabular-nums">{fmt(s.stat.mean)} [{fmt(s.stat.low)}; {fmt(s.stat.high)}] n={s.stat.n}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
