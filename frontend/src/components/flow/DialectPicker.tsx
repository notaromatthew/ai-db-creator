export type Dialect = 'postgresql' | 'mysql' | 'mssql' | 'sqlite' | 'oracle'

export const DIALECTS: { id: Dialect; label: string; hint: string }[] = [
  { id: 'postgresql', label: 'PostgreSQL', hint: 'Consigliato' },
  { id: 'mysql', label: 'MySQL e MariaDB', hint: 'Tipi INT, DATETIME' },
  { id: 'mssql', label: 'SQL Server', hint: 'Tipi NVARCHAR, BIT' },
  { id: 'oracle', label: 'Oracle', hint: 'Tipi VARCHAR2, NUMBER' },
  { id: 'sqlite', label: 'SQLite', hint: 'File singolo, test locali' },
]

export const dialectLabel = (id: string) => DIALECTS.find((d) => d.id === id)?.label ?? id

interface Props {
  value: Dialect
  onChange: (dialect: Dialect) => void
  disabled?: boolean
}

export default function DialectPicker({ value, onChange, disabled }: Props) {
  return (
    <div role="radiogroup" aria-label="Database di destinazione" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
      {DIALECTS.map((d) => {
        const checked = d.id === value
        return (
          <button
            key={d.id}
            type="button"
            role="radio"
            aria-checked={checked}
            disabled={disabled}
            onClick={() => onChange(d.id)}
            className={`flex items-center gap-3 rounded-xl border p-3 text-left transition disabled:opacity-60 ${checked ? 'border-orange-500 bg-orange-500/10' : 'border-tecnia-line bg-white/60 hover:border-orange-300 dark:border-slate-600 dark:bg-slate-800/60'}`}
          >
            <span className="material-symbols-outlined text-tecnia-primary dark:text-orange-300" aria-hidden="true" style={checked ? { fontVariationSettings: "'FILL' 1" } : undefined}>
              {checked ? 'radio_button_checked' : 'radio_button_unchecked'}
            </span>
            <span className="min-w-0">
              <b className="block font-headline text-sm">{d.label}</b>
              <span className="block text-xs text-tecnia-muted dark:text-slate-400">{d.hint}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
