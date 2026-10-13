interface Props {
  finalized: boolean
  version?: number
}

export default function SchemaStatusBadge({ finalized, version }: Props) {
  return (
    <span className={`tag inline-flex items-center gap-1 ${finalized ? 'text-tecnia-ok dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300'}`}>
      <span className="material-symbols-outlined text-[16px]" aria-hidden="true">{finalized ? 'lock' : 'edit_note'}</span>
      {finalized ? 'Definitivo' : 'Bozza'}
      {version ? <span> · versione {version}</span> : null}
    </span>
  )
}
