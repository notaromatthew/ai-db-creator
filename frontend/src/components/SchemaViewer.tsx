import { NormalizedSchema, TableDef, ColumnDef } from '@/types'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/api/client'
import { useQueryClient } from '@tanstack/react-query'

interface Props {
  schema: NormalizedSchema
  projectId: string
  /** Ruolo di sola lettura: nasconde la modifica manuale. */
  readOnly?: boolean
  /** Salva da solo le modifiche a mano dopo una breve pausa (ms). 0 o assente: solo con il pulsante Salva. */
  autosaveMs?: number
}

const defaultColumn = (): ColumnDef => ({
  name: '',
  data_type: 'TEXT',
  is_primary_key: false,
  is_foreign_key: false,
  is_unique: false,
  is_not_null: false,
})

export default function SchemaViewer({ schema, projectId, readOnly = false, autosaveMs = 0 }: Props) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [localSchema, setLocalSchema] = useState<NormalizedSchema>(schema)

  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const lastSaved = useRef(JSON.stringify(schema))

  useEffect(() => {
    lastSaved.current = JSON.stringify(schema)
    setLocalSchema(schema)
  }, [schema])

  // Salvataggio automatico con debounce: non ricarica lo schema, così non si perde ciò che stai scrivendo.
  useEffect(() => {
    if (!autosaveMs || !editing) return
    const snapshot = JSON.stringify(localSchema)
    if (snapshot === lastSaved.current) return
    const timer = window.setTimeout(async () => {
      setSaveState('saving')
      try {
        await api.put(`/projects/${projectId}/schema`, JSON.parse(snapshot))
        lastSaved.current = snapshot
        setSaveState('saved')
        queryClient.invalidateQueries({ queryKey: ['schema-versions', projectId] })
        queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      } catch {
        setSaveState('error')
      }
    }, autosaveMs)
    return () => window.clearTimeout(timer)
  }, [localSchema, editing, autosaveMs, projectId, queryClient])

  const handleUpdate = async () => {
    await api.put(`/projects/${projectId}/schema`, localSchema)
    queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
    queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    setEditing(false)
  }

  const toggleEditing = () => {
    if (editing) setLocalSchema(schema)
    setEditing(!editing)
  }

  const updateColumn = (tableIdx: number, colIdx: number, field: string, value: any) => {
    const updated = { ...localSchema }
    const col = { ...updated.tables[tableIdx].columns[colIdx] } as any
    col[field] = value
    updated.tables[tableIdx].columns[colIdx] = col
    setLocalSchema(updated)
  }

  const addColumn = (tableIdx: number) => {
    const updated = { ...localSchema }
    updated.tables[tableIdx].columns.push(defaultColumn())
    setLocalSchema(updated)
  }

  const removeColumn = (tableIdx: number, colIdx: number) => {
    const updated = { ...localSchema }
    updated.tables[tableIdx].columns.splice(colIdx, 1)
    setLocalSchema(updated)
  }

  const addTable = () => {
    const updated = { ...localSchema }
    const name = `nuova_tabella_${updated.tables.length + 1}`
    updated.tables.push({ name, columns: [{ ...defaultColumn(), name: 'id', data_type: 'INTEGER', is_primary_key: true }] })
    setLocalSchema(updated)
  }

  const removeTable = (tableIdx: number) => {
    const updated = { ...localSchema }
    updated.tables.splice(tableIdx, 1)
    setLocalSchema(updated)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Struttura delle tabelle</h2>
        <div className="flex gap-2">
          {editing && (
            <button onClick={addTable} className="bg-green-600 text-white px-3 py-1 rounded text-sm">
              + Aggiungi tabella
            </button>
          )}
          {editing ? (
            <div className="space-x-2">
              <button onClick={handleUpdate} className="primary-button min-h-9 px-4">
                Salva
              </button>
              <button onClick={toggleEditing} className="secondary-button min-h-9 px-4">
                Annulla
              </button>
            </div>
          ) : (
            !readOnly && (
              <button onClick={toggleEditing} className="secondary-button min-h-9 px-4">
                Modifica a mano
              </button>
            )
          )}
        </div>
      </div>

      {autosaveMs > 0 && editing && (
        <p className={`text-xs ${saveState === 'error' ? 'text-red-600' : 'text-tecnia-muted dark:text-slate-400'}`} role="status" aria-live="polite">
          {saveState === 'saving' ? 'Salvo le modifiche…' : saveState === 'saved' ? 'Modifiche salvate in bozza.' : saveState === 'error' ? 'Non sono riuscito a salvare: riprova con il pulsante Salva.' : 'Le modifiche si salvano da sole.'}
        </p>
      )}

      {localSchema.description && <p className="text-gray-600">{localSchema.description}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {localSchema.tables.map((table: TableDef, ti: number) => (
          <div key={table.name} className="border rounded p-4 bg-white dark:bg-gray-800 dark:border-gray-600">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-bold text-lg">{table.name}</h3>
              {editing && (
                <button onClick={() => removeTable(ti)} className="text-red-600 hover:text-red-800 text-xs">
                  Elimina tabella
                </button>
              )}
            </div>
            {table.description && <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">{table.description}</p>}
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left">Colonna</th>
                  <th className="text-left">Tipo</th>
                  <th className="text-left" title="Chiave primaria">Chiave</th>
                  <th className="text-left" title="Chiave esterna">Collegata a</th>
                  <th className="text-left" title="Valore obbligatorio">Obbligatorio</th>
                  {editing && <th className="w-8"></th>}
                </tr>
              </thead>
              <tbody>
                {table.columns.map((col, ci) => (
                  <tr key={ci}>
                    {editing ? (
                      <>
                        <td><input className="border rounded px-1 w-full text-sm dark:bg-gray-700 dark:text-white dark:border-gray-500" value={col.name} onChange={e => updateColumn(ti, ci, 'name', e.target.value)} /></td>
                        <td><input className="border rounded px-1 w-20 text-sm dark:bg-gray-700 dark:text-white dark:border-gray-500" value={col.data_type} onChange={e => updateColumn(ti, ci, 'data_type', e.target.value)} /></td>
                        <td><input type="checkbox" checked={col.is_primary_key} onChange={e => updateColumn(ti, ci, 'is_primary_key', e.target.checked)} /></td>
                        <td><input type="checkbox" checked={col.is_foreign_key} onChange={e => updateColumn(ti, ci, 'is_foreign_key', e.target.checked)} /></td>
                        <td><input type="checkbox" checked={col.is_not_null} onChange={e => updateColumn(ti, ci, 'is_not_null', e.target.checked)} /></td>
                        <td><button onClick={() => removeColumn(ti, ci)} className="text-red-600 hover:text-red-800 text-xs" title="Elimina colonna">&times;</button></td>
                      </>
                    ) : (
                      <>
                        <td>{col.name}</td>
                        <td>{col.data_type}</td>
                        <td>{col.is_primary_key ? 'Sì' : ''}</td>
                        <td>{col.is_foreign_key ? `${col.foreign_key_table}.${col.foreign_key_column}` : ''}</td>
                        <td>{col.is_not_null ? 'Sì' : ''}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {editing && (
              <button onClick={() => addColumn(ti)} className="text-blue-600 hover:text-blue-800 text-xs mt-2">
                + Aggiungi colonna
              </button>
            )}
          </div>
        ))}
      </div>

      {localSchema.relationships.length > 0 && (
        <div className="mt-6">
          <h3 className="font-semibold mb-2">Relazioni</h3>
          <div className="space-y-2">
            {localSchema.relationships.map((rel, i) => (
              <div key={i} className="text-sm flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded">
                <span className="font-mono">{rel.from_table}.{rel.from_column}</span>
                <span className="text-gray-400">
                  {rel.type === 'one_to_many' ? '──N──→' : rel.type === 'many_to_many' ? '──M:N──' : '──1:1──'}
                </span>
                <span className="font-mono">{rel.to_table}.{rel.to_column}</span>
                <span className="text-xs text-gray-500 ml-1">({rel.type === 'one_to_many' ? 'uno a molti' : rel.type === 'many_to_many' ? 'molti a molti' : 'uno a uno'})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
