import { useState } from 'react'
import { api } from '@/api/client'

interface Props {
  projectId: string
}

const dialects = ['sqlite', 'postgresql', 'mysql', 'mssql'] as const

export default function ExportButton({ projectId }: Props) {
  const [showOptions, setShowOptions] = useState(false)
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: string) => {
    setExporting(true)
    try {
      const data = await api.get(`/projects/${projectId}/export?format=${format}`)
      const content = data.content

      const blob = new Blob([content], {
        type: format === 'sql' ? 'text/sql' : format === 'json' ? 'application/json' : 'text/csv',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `schema_${projectId}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
    } finally {
      setExporting(false)
      setShowOptions(false)
    }
  }

  const handleExportFull = async (dialect: string) => {
    setExporting(true)
    try {
      const data = await api.get(`/projects/${projectId}/export-full?dialect=${dialect}`)
      const content = data.content

      const blob = new Blob([content], { type: 'text/sql' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `db_${projectId}_${dialect}.sql`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error(e)
    } finally {
      setExporting(false)
      setShowOptions(false)
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setShowOptions(!showOptions)}
        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm hover:bg-gray-300 dark:hover:bg-gray-600"
        disabled={exporting}
      >
        {exporting ? 'Exporting...' : 'Export'}
      </button>
      {showOptions && (
        <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-10 min-w-40">
          <div className="px-3 py-1 text-xs text-gray-500 uppercase tracking-wider">Schema only</div>
          <button onClick={() => handleExport('sql')} className="block w-full px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-left">SQL (DDL)</button>
          <button onClick={() => handleExport('json')} className="block w-full px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-left">JSON</button>
          <button onClick={() => handleExport('csv')} className="block w-full px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-left">CSV</button>
          <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>
          <div className="px-3 py-1 text-xs text-gray-500 uppercase tracking-wider">Full DB (DDL + Data)</div>
          {dialects.map(d => (
            <button key={d} onClick={() => handleExportFull(d)} className="block w-full px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-left capitalize">{d}</button>
          ))}
        </div>
      )}
    </div>
  )
}