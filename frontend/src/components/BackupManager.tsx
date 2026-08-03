import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

interface Props {
  projectId: string
}

export default function BackupManager({ projectId }: Props) {
  const [open, setOpen] = useState(false)
  const [label, setLabel] = useState('')
  const queryClient = useQueryClient()

  const { data: backups, refetch } = useQuery({
    queryKey: ['backups', projectId],
    queryFn: () => api.get(`/projects/${projectId}/backups`),
    enabled: false,
  })

  const backupMut = useMutation({
    mutationFn: (lbl: string) => api.post(`/projects/${projectId}/backup?label=${encodeURIComponent(lbl)}`, {}),
    onSuccess: () => {
      setLabel('')
      refetch()
    },
  })

  const restoreMut = useMutation({
    mutationFn: (name: string) => api.post(`/projects/${projectId}/restore`, { backup_name: name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      refetch()
    },
  })

  const handleToggle = () => {
    setOpen(!open)
    if (!open) refetch()
  }

  const handleRestore = (name: string) => {
    if (window.confirm(`Ripristinare il backup "${name}"? I dati correnti verranno salvati come undo.`)) {
      restoreMut.mutate(name)
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={handleToggle}
        className="px-3 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm hover:bg-gray-300 dark:hover:bg-gray-600"
      >
        Backup / Restore
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-20 min-w-80 p-3">
          <h4 className="font-semibold mb-2">Backup del database</h4>

          <div className="flex gap-2 mb-3">
            <input
              type="text"
              placeholder="Etichetta (opzionale)"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="flex-1 border rounded px-2 py-1 text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
            <button
              onClick={() => backupMut.mutate(label)}
              disabled={backupMut.isPending}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
            >
              {backupMut.isPending ? 'Salvataggio...' : 'Crea backup'}
            </button>
          </div>

          {restoreMut.isPending && <p className="text-blue-500 text-sm mb-2">Ripristino in corso...</p>}

          {backups && backups.length > 0 && (
            <div>
              <h5 className="text-sm font-medium mb-1">Backup disponibili:</h5>
              <div className="max-h-60 overflow-y-auto space-y-1">
                {backups.map((b: any) => (
                  <div key={b.file} className="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-700 rounded p-1.5">
                    <div className="flex-1 min-w-0 mr-2">
                      <div className="truncate font-medium">{b.label || b.file}</div>
                      <div className="text-gray-500">
                        {new Date(b.timestamp).toLocaleString()} &middot; {(b.size / 1024).toFixed(1)} KB
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestore(b.file)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 shrink-0"
                    >
                      Ripristina
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          {backups && backups.length === 0 && (
            <p className="text-gray-500 text-sm">Nessun backup disponibile.</p>
          )}
        </div>
      )}
    </div>
  )
}
