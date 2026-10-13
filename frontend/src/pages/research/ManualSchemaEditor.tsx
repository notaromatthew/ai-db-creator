import { useState } from 'react'

export interface EditorColumn { name: string; type: string; primary_key: boolean; nullable: boolean; references: string }
export interface EditorTable { name: string; columns: EditorColumn[] }

const TYPES = ['INTEGER', 'TEXT', 'REAL', 'DATE', 'BOOLEAN']
const emptyColumn = (): EditorColumn => ({ name: '', type: 'TEXT', primary_key: false, nullable: true, references: '' })
const input = 'rounded-lg border border-tecnia-line bg-white/80 px-2 py-1.5 text-sm dark:bg-slate-900'

/** Editor di schema senza intelligenza artificiale (braccio manuale): solo tabelle, colonne, chiavi e relazioni. */
export default function ManualSchemaEditor({ onSave, saving, saved, error }: {
  onSave: (tables: { name: string; columns: { name: string; type: string; primary_key: boolean; nullable: boolean; references: string | null }[] }[]) => void
  saving?: boolean; saved?: boolean; error?: string
}) {
  const [tables, setTables] = useState<EditorTable[]>([{ name: '', columns: [emptyColumn()] }])
  const [touched, setTouched] = useState(false)

  const update = (next: EditorTable[]) => { setTables(next); setTouched(true) }
  const setTable = (i: number, patch: Partial<EditorTable>) => update(tables.map((t, k) => (k === i ? { ...t, ...patch } : t)))
  const setColumn = (i: number, j: number, patch: Partial<EditorColumn>) =>
    setTable(i, { columns: tables[i].columns.map((c, k) => (k === j ? { ...c, ...patch } : c)) })

  const valid = tables.length > 0 && tables.every((t) => t.name.trim() && t.columns.length > 0 && t.columns.every((c) => c.name.trim()))
  const submit = () => { setTouched(false); onSave(tables.map((t) => ({
    name: t.name.trim(),
    columns: t.columns.map((c) => ({ ...c, name: c.name.trim(), references: c.references.trim() || null })),
  }))) }

  return (
    <section className="flex flex-col gap-4" aria-label="Editor dello schema">
      <p className="text-sm text-tecnia-muted dark:text-slate-300">Aggiungi le tabelle e le loro colonne. Per una relazione, scrivi nella colonna "Riferimento" la tabella e la colonna a cui punta, per esempio <code>autori.id</code>.</p>
      {tables.map((t, i) => (
        <fieldset key={i} className="glass flex flex-col gap-3 p-4">
          <legend className="sr-only">Tabella {i + 1}</legend>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1 text-xs font-semibold">Nome della tabella
              <input className={input} value={t.name} onChange={(e) => setTable(i, { name: e.target.value })} placeholder="libri" maxLength={60} />
            </label>
            {tables.length > 1 && <button type="button" className="secondary-button !min-h-8 !px-3" onClick={() => update(tables.filter((_, k) => k !== i))}>Togli la tabella</button>}
          </div>
          <div className="flex flex-col gap-2">
            {t.columns.map((c, j) => (
              <div key={j} className="flex flex-wrap items-end gap-2 rounded-xl border border-tecnia-line/50 p-2">
                <label className="flex flex-col gap-1 text-xs font-semibold">Colonna
                  <input className={input} value={c.name} onChange={(e) => setColumn(i, j, { name: e.target.value })} aria-label={`Nome colonna ${j + 1} della tabella ${i + 1}`} maxLength={60} />
                </label>
                <label className="flex flex-col gap-1 text-xs font-semibold">Tipo
                  <select className={input} value={c.type} onChange={(e) => setColumn(i, j, { type: e.target.value })} aria-label={`Tipo colonna ${j + 1} della tabella ${i + 1}`}>{TYPES.map((x) => <option key={x}>{x}</option>)}</select>
                </label>
                <label className="flex items-center gap-1.5 pb-1.5 text-xs"><input type="checkbox" checked={c.primary_key} onChange={(e) => setColumn(i, j, { primary_key: e.target.checked, nullable: e.target.checked ? false : c.nullable })} />Chiave primaria</label>
                <label className="flex items-center gap-1.5 pb-1.5 text-xs"><input type="checkbox" checked={!c.nullable} onChange={(e) => setColumn(i, j, { nullable: !e.target.checked })} />Obbligatoria</label>
                <label className="flex flex-col gap-1 text-xs font-semibold">Riferimento
                  <input className={`${input} w-36`} value={c.references} onChange={(e) => setColumn(i, j, { references: e.target.value })} placeholder="tabella.colonna" aria-label={`Riferimento colonna ${j + 1} della tabella ${i + 1}`} />
                </label>
                {t.columns.length > 1 && (
                  <button type="button" className="secondary-button !min-h-8 !px-3" onClick={() => setTable(i, { columns: t.columns.filter((_, k) => k !== j) })} aria-label={`Togli la colonna ${j + 1} della tabella ${i + 1}`}>
                    <span aria-hidden="true" className="material-symbols-outlined !text-[18px]">delete</span>
                  </button>
                )}
              </div>
            ))}
          </div>
          <div><button type="button" className="secondary-button !min-h-8" onClick={() => setTable(i, { columns: [...t.columns, emptyColumn()] })}>
            <span aria-hidden="true" className="material-symbols-outlined !text-[18px]">add</span> Aggiungi una colonna</button></div>
        </fieldset>
      ))}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="secondary-button" onClick={() => update([...tables, { name: '', columns: [emptyColumn()] }])}>
          <span aria-hidden="true" className="material-symbols-outlined !text-[18px]">add</span> Aggiungi una tabella</button>
        <button type="button" className="primary-button" disabled={!valid || saving} onClick={submit}>Salva lo schema</button>
        {saved && !touched && <span role="status" className="text-sm text-tecnia-ok">Schema salvato.</span>}
        {!valid && <span className="text-xs text-tecnia-muted">Dai un nome a ogni tabella e a ogni colonna.</span>}
      </div>
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
    </section>
  )
}
