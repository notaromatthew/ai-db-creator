import { useState } from 'react'
import { api } from '@/api/client'
import { NormalizedSchema, ExecuteQueryResponse } from '@/types'

interface Props {
  projectId: string
  schema: NormalizedSchema
  onDataChange?: () => void
}

export default function QueryBuilder({ projectId, schema, onDataChange }: Props) {
  const [mode, setMode] = useState<'nl' | 'sql'>('nl')
  const [prompt, setPrompt] = useState('')
  const [directSql, setDirectSql] = useState('')
  const [sql, setSql] = useState('')
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ExecuteQueryResponse | null>(null)

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api.post(`/projects/${projectId}/query`, { prompt, dialect: 'sqlite' })
      setSql(res.sql)
    } catch (e) {
      setError('Failed to generate query. Check your prompt and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleExecute = async (query: string) => {
    if (!query.trim()) return
    setExecuting(true)
    setError('')
    setResult(null)
    try {
      const res = await api.post(`/projects/${projectId}/execute-query`, { sql: query })
      setResult(res)
      onDataChange?.()
    } catch (e: any) {
      setError(e?.message || 'Query execution failed.')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 mb-2">
        <button
          onClick={() => setMode('nl')}
          className={`px-3 py-1 rounded text-sm ${mode === 'nl' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
        >
          Query assistita
        </button>
        <button
          onClick={() => setMode('sql')}
          className={`px-3 py-1 rounded text-sm ${mode === 'sql' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
        >
          SQL diretto
        </button>
      </div>

      {mode === 'nl' ? (
        <div className="bg-white dark:bg-gray-800 p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Descrivi in italiano la query</h3>
          <textarea
            placeholder="es. Mostra tutti i prodotti con prezzo > 100"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full p-2 border rounded h-20 dark:bg-gray-700 dark:text-white"
            disabled={loading}
          />
          <button
            onClick={handleGenerate}
            disabled={!prompt.trim() || loading}
            className="bg-blue-600 text-white px-4 py-2 rounded mt-2 disabled:opacity-50"
          >
            {loading ? 'Generazione...' : 'Genera SQL'}
          </button>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Scrivi SQL direttamente</h3>
          <textarea
            placeholder="SELECT * FROM clienti;"
            value={directSql}
            onChange={(e) => setDirectSql(e.target.value)}
            className="w-full p-2 border rounded h-20 font-mono text-sm dark:bg-gray-700 dark:text-white"
          />
          <button
            onClick={() => handleExecute(directSql)}
            disabled={!directSql.trim() || executing}
            className="bg-green-600 text-white px-4 py-2 rounded mt-2 disabled:opacity-50"
          >
            {executing ? 'Esecuzione...' : 'Esegui'}
          </button>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>
      )}

      {mode === 'nl' && sql && (
        <div className="bg-white dark:bg-gray-800 p-4 rounded shadow">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">SQL generato</h3>
            <button
              onClick={() => handleExecute(sql)}
              disabled={executing}
              className="bg-green-600 text-white px-4 py-2 rounded disabled:opacity-50 text-sm"
            >
              {executing ? 'Esecuzione...' : 'Esegui'}
            </button>
          </div>
          <pre className="bg-gray-100 dark:bg-gray-700 p-3 rounded text-sm overflow-x-auto">{sql}</pre>
        </div>
      )}

      {result && (
        <div className="bg-white dark:bg-gray-800 p-4 rounded shadow">
          <h3 className="font-semibold mb-2">
            Risultati{result.affected !== null ? ` (${result.affected} righe)` : ''}
          </h3>
          {result.columns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-gray-100 dark:bg-gray-700">
                    {result.columns.map((col) => (
                      <th key={col} className="border p-2 text-left font-medium">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-900'}>
                      {result.columns.map((col) => (
                        <td key={col} className="border p-2">{String(row[col] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Esecuzione completata ({result.affected} righe interessate).</p>
          )}
        </div>
      )}
    </div>
  )
}
