import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

interface Props {
  projectId: string
}

export default function ProgressBar({ projectId }: Props) {
  const { data: progress } = useQuery({
    queryKey: ['progress', projectId],
    queryFn: () => api.get(`/progress/${projectId}`),
    refetchInterval: 1000,
    enabled: true,
  })

  if (!progress || progress.status === 'idle') return null

  return (
    <div className="fixed bottom-20 left-4 right-4 z-40 mx-auto max-w-md rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-900/95" role="status" aria-live="polite">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium">{progress.message || progress.status}</span>
        <span className="text-sm text-gray-500 dark:text-gray-400">{progress.progress}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress.progress}%` }}
        />
      </div>
    </div>
  )
}
