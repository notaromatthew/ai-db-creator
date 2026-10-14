import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export default function LLMStatus() {
  const { data: info } = useQuery({
    queryKey: ['llm-info'],
    queryFn: () => api.get('/llm/info'),
    refetchInterval: 30000,
  })

  if (!info) return null

  return (
    <div className="fixed bottom-4 right-4 z-30 rounded-full border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95" title="Modello IA attivo" role="status" aria-label="Modello IA attivo">
      <div className="flex items-center gap-2">
        <div aria-hidden="true" className={`w-2 h-2 rounded-full bg-blue-500`}></div>
        <span className="font-medium">
          {info.provider}: {info.model}
        </span>
      </div>
    </div>
  )
}
