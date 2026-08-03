import { useState, useCallback, useEffect } from 'react'
import { NormalizedSchema } from '@/types'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

interface Props {
  projectId: string
  schema: NormalizedSchema
  autoLoad?: boolean
}

type EditingState = Record<string, Record<number, Record<string, string>>>

export default function DataViewer({ projectId, schema, autoLoad }: Props) {
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [tableData, setTableData] = useState<Record<string, any[]>>({})
  const [search, setSearch] = useState('')
  const [columnFilters, setColumnFilters] = useState<Record<string, Record<string, string>>>({})
  const [editing, setEditing] = useState<EditingState>({})
  const [newRows, setNewRows] = useState<Record<string, Record<string, string>[]>>({})

  useEffect(() => {
    if (autoLoad) loadData()
  }, [autoLoad])

  const invalidateStats = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
  }, [queryClient, projectId])

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    const results: Record<string, any[]> = {}
    for (const table of schema.tables) {
      try {
        results[table.name] = await api.get(`/projects/${projectId}/data/${table.name}`)
      } catch {
        results[table.name] = []
      }
    }
    setTableData(results)
    setLoading(false)
  }, [projectId, schema])

  const pkCols = (tableName: string) => {
    const t = schema.tables.find(t => t.name === tableName)
    return t ? t.columns.filter(c => c.is_primary_key).map(c => c.name) : []
  }

  const colNames = (tableName: string) => {
    const t = schema.tables.find(t => t.name === tableName)
    return t ? t.columns.map(c => c.name) : []
  }

  const visibleRows = (tableName: string, rows: any[]) => {
    const cols = colNames(tableName)
    const filters = columnFilters[tableName] || {}
    return rows.filter(row => {
      if (search) {
        const q = search.toLowerCase()
        if (!cols.some(c => String(row[c] ?? '').toLowerCase().includes(q))) return false
      }
      for (const [col, val] of Object.entries(filters)) {
        if (!val) continue
        if (!String(row[col] ?? '').toLowerCase().includes(val.toLowerCase())) return false
      }
      return true
    })
  }

  const exportCsv = (tableName: string, rows: any[]) => {
    const cols = colNames(tableName)
    const filtered = visibleRows(tableName, rows)
    const header = cols.join(',')
    const lines = filtered.map(r => cols.map(c => {
      const v = r[c]
      if (v === null || v === undefined) return ''
      const s = String(v)
      return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
    }).join(','))
    const csv = [header, ...lines].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${tableName}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const editCell = (table: string, rowIdx: number, col: string, val: string) => {
    setEditing(prev => ({
      ...prev,
      [table]: {
        ...(prev[table] || {}),
        [rowIdx]: { ...((prev[table] || {})[rowIdx] || {}), [col]: val },
      },
    }))
  }

  const editNewCell = (table: string, rowIdx: number, col: string, val: string) => {
    setNewRows(prev => {
      const rows = [...(prev[table] || [])]
      rows[rowIdx] = { ...(rows[rowIdx] || {}), [col]: val }
      return { ...prev, [table]: rows }
    })
  }

  const saveRow = async (table: string, rowIdx: number) => {
    const edits = editing[table]?.[rowIdx]
    if (!edits) return
    const row = tableData[table]?.[rowIdx]
    const merged = { ...row, ...edits }
    try {
      await api.put(`/projects/${projectId}/data/${table}`, merged)
      setEditing(prev => {
        const next = { ...prev }
        delete next[table]?.[rowIdx]
        if (next[table] && !Object.keys(next[table]).length) delete next[table]
        return next
      })
      await loadData()
      invalidateStats()
    } catch (e: any) {
      setError(e?.message || 'Update failed')
    }
  }

  const deleteRow = async (table: string, row: any) => {
    const pks = pkCols(table)
    const pkVals: Record<string, any> = {}
    for (const pk of pks) pkVals[pk] = row[pk]
    try {
      await api.delete(`/projects/${projectId}/data/${table}`, { pks: pkVals })
      await loadData()
      invalidateStats()
    } catch (e: any) {
      setError(e?.message || 'Delete failed')
    }
  }

  const addRow = async (table: string) => {
    const rows = newRows[table]
    if (!rows || !rows.length) return
    for (let i = 0; i < rows.length; i++) {
      try {
        await api.post(`/projects/${projectId}/data/${table}`, rows[i])
      } catch (e: any) {
        setError(e?.message || `Insert failed for row ${i + 1}`)
        return
      }
    }
    setNewRows(prev => ({ ...prev, [table]: [] }))
    await loadData()
    invalidateStats()
  }

  const addEmptyRow = (table: string) => {
    setNewRows(prev => ({
      ...prev,
      [table]: [...(prev[table] || []), {}],
    }))
  }

  const cellVal = (table: string, rowIdx: number, col: string, origVal: any) => {
    return editing[table]?.[rowIdx]?.[col] ?? (origVal !== null && origVal !== undefined ? String(origVal) : '')
  }

  const isCellEdited = (table: string, rowIdx: number, col: string) => {
    return col in ((editing[table] || {})[rowIdx] || {})
  }

  const hasFilter = Object.values(columnFilters).some(tf => tf && Object.values(tf).some(v => v)) || search

  return (
    <div className="space-y-6">
      <div className="flex gap-2 items-center flex-wrap">
        <button onClick={loadData} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50">
          {loading ? 'Loading...' : 'Load Data'}
        </button>
        <input
          placeholder="Cerca in tutte le tabelle..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-white flex-1 min-w-[200px]"
        />
        {hasFilter && (
          <button onClick={() => { setSearch(''); setColumnFilters({}) }} className="text-xs text-red-500 hover:text-red-700">
            Cancella filtri
          </button>
        )}
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </div>
      {Object.entries(tableData).length === 0 && loading && <p className="text-gray-500">Caricamento dati in corso...</p>}
      {Object.entries(tableData).length > 0 && Object.entries(tableData).map(([tableName, rows]) => {
        const filtered = visibleRows(tableName, rows)
        const cols = colNames(tableName)
        return (
          <div key={tableName} className="border rounded dark:border-gray-600">
            <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-700">
              <h3 className="font-bold">{tableName} <span className="text-xs font-normal text-gray-500">({filtered.length}/{rows.length} righe)</span></h3>
              <div className="flex gap-2 items-center">
                <button onClick={() => addEmptyRow(tableName)} className="text-green-600 hover:text-green-800 text-xs font-medium">
                  + Aggiungi riga
                </button>
                <button onClick={() => exportCsv(tableName, rows)} className="text-blue-600 hover:text-blue-800 text-xs">
                  Scarica CSV
                </button>
              </div>
            </div>
            {rows.length > 0 || hasFilter || (newRows[tableName]?.length || 0) > 0 ? (
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      {cols.map(key => (
                        <th key={key} className="text-left p-1.5 border dark:border-gray-600 text-xs text-gray-900 dark:text-gray-100">
                          <div className="font-medium mb-1">{key}</div>
                          <input
                            placeholder="Filtra..."
                            value={columnFilters[tableName]?.[key] || ''}
                            onChange={e => setColumnFilters(prev => ({
                              ...prev,
                              [tableName]: { ...(prev[tableName] || {}), [key]: e.target.value },
                            }))}
                            className="w-full border rounded px-1 py-0.5 text-[10px] dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                          />
                        </th>
                      ))}
                      <th className="p-1.5 border dark:border-gray-600 text-xs w-28">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 && !(newRows[tableName]?.length) ? (
                      <tr><td colSpan={cols.length + 1} className="p-2 text-gray-500 text-center">Nessun risultato</td></tr>
                    ) : (
                      <>
                        {filtered.map((row: any, i: number) => (
                          <tr key={i} className={i % 2 === 0 ? 'bg-gray-50 dark:bg-gray-800' : 'bg-gray-100 dark:bg-gray-900'}>
                            {cols.map(col => (
                              <td key={col} className={`p-1 border dark:border-gray-600 text-xs whitespace-nowrap ${isCellEdited(tableName, i, col) ? 'bg-yellow-100 dark:bg-yellow-900' : ''}`}>
                                <input
                                  value={cellVal(tableName, i, col, row[col])}
                                  onChange={(e) => editCell(tableName, i, col, e.target.value)}
                                  className="w-full bg-transparent outline-none text-gray-900 dark:text-gray-100"
                                />
                              </td>
                            ))}
                            <td className="p-1 border dark:border-gray-600 text-xs whitespace-nowrap">
                              <button onClick={() => saveRow(tableName, i)} className="text-green-600 hover:text-green-800 mr-2">Salva</button>
                              <button onClick={() => deleteRow(tableName, row)} className="text-red-600 hover:text-red-800">Elimina</button>
                            </td>
                          </tr>
                        ))}
                        {(newRows[tableName] || []).map((row, i) => (
                          <tr key={`new-${i}`} className="bg-green-50 dark:bg-green-900/20">
                            {cols.map(col => (
                              <td key={col} className="p-1 border dark:border-gray-600 text-xs">
                                <input
                                  value={row[col] || ''}
                                  onChange={(e) => editNewCell(tableName, i, col, e.target.value)}
                                  className="w-full bg-transparent outline-none text-gray-900 dark:text-gray-100"
                                  placeholder={col}
                                />
                              </td>
                            ))}
                            <td className="p-1 border dark:border-gray-600 text-xs">
                              {i === (newRows[tableName]?.length || 0) - 1 && (
                                <button onClick={() => addRow(tableName)} className="text-green-600 hover:text-green-800">Inserisci</button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="p-2 text-gray-500">Nessun dato. Vai su Schema e clicca "Populate Tables".</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
