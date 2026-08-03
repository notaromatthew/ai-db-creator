import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export default function LLMStatus() {
  const { data: info } = useQuery({
    queryKey: ['llm-info'],
    queryFn: () => api.get('/llm/info'),
    refetchInterval: 30000,
  })

  if (!info) return null

  const isLocal = info.provider.toLowerCase().includes('ollama')
  const isFree = info.provider.toLowerCase().includes('groq')

  return (
    <div className="fixed bottom-4 right-4 z-30 rounded-full border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95" title="Modello IA attivo">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isLocal ? 'bg-green-500' : isFree ? 'bg-purple-500' : 'bg-blue-500'}`}></div>
        <span className="font-medium">
          {info.provider}: {info.model}
        </span>
      </div>
    </div>
  )
}
