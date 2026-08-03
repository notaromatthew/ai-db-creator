import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useState } from 'react'

interface Props {
  projectId: string
}

const ICONS: Record<string, string> = {
  populate: '📦',
  import_sql: '📥',
  backup: '💾',
  restore: '⏪',
  execute_query: '▶️',
  chat: '💬',
  generate: '⚡',
}

export default function OperationHistory({ projectId }: Props) {
  const [open, setOpen] = useState(false)

  const { data: events } = useQuery({
    queryKey: ['interactions', projectId],
    queryFn: () => api.get(`/projects/${projectId}/interactions`),
    enabled: open,
  })

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm hover:bg-gray-300 dark:hover:bg-gray-600"
      >
        Storico
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-20 min-w-80 max-h-96 overflow-y-auto p-3">
          <h4 className="font-semibold mb-2 text-sm">Storico operazioni</h4>
          {!events || events.length === 0 ? (
            <p className="text-gray-500 text-xs">Nessuna operazione registrata.</p>
          ) : (
            <div className="space-y-1">
              {events.slice().reverse().map((e: any, i: number) => (
                <div key={i} className="text-xs border-b dark:border-gray-700 pb-1 last:border-0">
                  <div className="flex items-center gap-1">
                    <span>{ICONS[e.event_type] || '•'}</span>
                    <span className="font-medium capitalize">{e.event_type.replace(/_/g, ' ')}</span>
                    <span className="text-gray-500 ml-auto">{new Date(e.timestamp).toLocaleString()}</span>
                  </div>
                  {e.data && Object.keys(e.data).length > 0 && (
                    <div className="text-gray-500 ml-4 truncate">{JSON.stringify(e.data).slice(0, 120)}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
