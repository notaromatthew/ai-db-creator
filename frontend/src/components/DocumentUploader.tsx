import { useEffect, useRef, useState } from 'react'
import { api } from '@/api/client'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { Document as ProjectDocument } from '@/types'

interface Props {
  projectId: string
  onUpload: () => void
  /** Sola lettura: nessun caricamento o rimozione. */
  readOnly?: boolean
}

const ACCEPTED_EXTENSIONS = ['pdf', 'xls', 'xlsx', 'txt', 'csv', 'sql']
const MAX_FILE_SIZE = 25 * 1024 * 1024
const MAX_RETRIES = 3
/** Attese prima di ogni nuovo tentativo automatico (backoff). */
export const RETRY_DELAYS_MS = [1000, 2000, 4000]

type ItemStatus = 'queued' | 'uploading' | 'waiting' | 'done' | 'error'
interface QueueItem { id: number; file: File; status: ItemStatus; attempt: number; error?: string }

const STATUS_LABEL: Record<ItemStatus, string> = {
  queued: 'In coda', uploading: 'In corso', waiting: 'Nuovo tentativo a breve', done: 'Caricato', error: 'Errore',
}
const STATUS_ICON: Record<ItemStatus, string> = {
  queued: 'schedule', uploading: 'sync', waiting: 'replay', done: 'check_circle', error: 'error',
}
/** Ritentabili: rete assente (0), tempo scaduto, troppe richieste, errori del server. */
const isRetryable = (e: unknown) => {
  const status = (e as { status?: number } | null)?.status
  return status === 0 || status === 408 || status === 429 || (typeof status === 'number' && status >= 500)
}
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentUploader({ projectId, onUpload, readOnly = false }: Props) {
  const [items, setItems] = useState<QueueItem[]>([])
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const nextId = useRef(1)
  const alive = useRef(true)
  const running = useRef(false)
  const queryClient = useQueryClient()
  const uploading = items.some((i) => i.status === 'uploading' || i.status === 'waiting')
  const pending = items.filter((i) => i.status === 'queued')

  useEffect(() => () => { alive.current = false }, [])

  const { data: documents = [] } = useQuery<ProjectDocument[]>({
    queryKey: ['documents', projectId],
    queryFn: () => api.get(`/projects/${projectId}/documents`),
    enabled: !!projectId,
  })

  const patch = (id: number, change: Partial<QueueItem>) =>
    alive.current && setItems((list) => list.map((i) => (i.id === id ? { ...i, ...change } : i)))

  const selectFiles = (picked?: FileList | File[] | null) => {
    setError('')
    setSuccess('')
    const list = Array.from(picked ?? [])
    if (!list.length) return
    const accepted: QueueItem[] = []
    const problems: string[] = []
    for (const f of list) {
      const extension = f.name.split('.').pop()?.toLowerCase() || ''
      if (!ACCEPTED_EXTENSIONS.includes(extension)) problems.push('Formato non supportato. Usa PDF, Excel, CSV, TXT o SQL.')
      else if (f.size > MAX_FILE_SIZE) problems.push('Il file supera il limite di 25 MB.')
      else accepted.push({ id: nextId.current++, file: f, status: 'queued', attempt: 0 })
    }
    // i file gia' caricati dell'elenco precedente si tolgono: restano in "File disponibili"
    setItems((current) => [...current.filter((i) => i.status !== 'done'), ...accepted])
    if (problems.length) setError(problems[0])
  }

  const removeItem = (id: number) => setItems((list) => list.filter((i) => i.id !== id))

  const refreshDocuments = async () => {
    await queryClient.invalidateQueries({ queryKey: ['documents', projectId] })
    onUpload()
  }

  /** Carica un solo file: ogni file si salva appena arriva, quindi un'interruzione perde solo quello in corso. */
  const uploadOne = async (item: QueueItem) => {
    const uploadedName = item.file.name
    let baselineIds = new Set(documents.map((document) => document.id))
    patch(item.id, { status: 'uploading', attempt: 0, error: undefined })
    try {
      const baseline: ProjectDocument[] = await api.get(`/projects/${projectId}/documents`)
      baselineIds = new Set(baseline.map((document) => document.id))
    } catch { /* si prosegue con l'elenco gia' noto */ }

    for (let attempt = 0; ; attempt++) {
      try {
        await api.postFile(`/projects/${projectId}/documents`, item.file)
        await refreshDocuments()
        if (alive.current) { setSuccess(`“${uploadedName}” è pronto per essere usato.`); patch(item.id, { status: 'done' }) }
        return
      } catch (uploadError: any) {
        // Un file Excel può terminare l'elaborazione sul server dopo che il browser
        // ha perso la risposta. Verifichiamo lo stato reale prima di mostrare errore.
        try {
          const latest: ProjectDocument[] = await api.get(`/projects/${projectId}/documents`)
          const isActuallyUploaded = latest.some(
            (document) => !baselineIds.has(document.id) && document.filename === uploadedName,
          )
          if (isActuallyUploaded) {
            await refreshDocuments()
            if (alive.current) { setSuccess(`“${uploadedName}” è stato caricato correttamente.`); patch(item.id, { status: 'done' }) }
            return
          }
        } catch {
          // Mantiene il messaggio originale se anche la verifica non è disponibile.
        }
        if (attempt < MAX_RETRIES && isRetryable(uploadError) && alive.current) {
          patch(item.id, { status: 'waiting', attempt: attempt + 1 })
          await sleep(RETRY_DELAYS_MS[attempt] ?? 4000)
          if (!alive.current) return
          patch(item.id, { status: 'uploading' })
          continue
        }
        const message = uploadError?.message || 'Non è stato possibile caricare il file. Riprova.'
        patch(item.id, { status: 'error', error: message })
        if (alive.current) setError(`${uploadedName}: ${message}`)
        return
      }
    }
  }

  const runQueue = async (list: QueueItem[]) => {
    if (running.current) return
    running.current = true
    setError('')
    setSuccess('')
    try {
      for (const item of list) await uploadOne(item)
    } finally {
      running.current = false
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleUpload = () => runQueue(pending)
  const retryItem = (item: QueueItem) => runQueue([item])

  const handleDelete = async (document: ProjectDocument) => {
    if (!window.confirm(`Rimuovere “${document.filename}”?`)) return
    setError('')
    try {
      await api.delete(`/projects/${projectId}/documents/${document.id}`)
      await queryClient.invalidateQueries({ queryKey: ['documents', projectId] })
    } catch {
      setError('Non è stato possibile rimuovere il documento.')
    }
  }

  return (
    <section className="surface overflow-hidden" aria-labelledby="documents-title">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-6 dark:border-slate-800">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-bold uppercase tracking-wider text-tecnia-primary">Documenti di partenza</p>
            <h2 id="documents-title" className="text-lg font-bold">I tuoi file</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">L'IA li userà per capire struttura e contenuti del database.</p>
          </div>
          <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {documents.length} file
          </span>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        {readOnly ? (
          <p className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-sm font-medium text-tecnia-muted dark:bg-slate-800 dark:text-slate-300">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span>Hai accesso in sola lettura: non puoi aggiungere né rimuovere file.
          </p>
        ) : (
        <div
          className={`rounded-3xl border-2 border-dashed p-6 text-center transition sm:p-10 ${dragging ? 'border-orange-500 bg-orange-500/10' : 'border-orange-500 bg-orange-500/5'}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); selectFiles(event.dataTransfer.files) }}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.xls,.xlsx,.txt,.csv,.sql"
            onChange={(event) => selectFiles(event.target.files)}
            className="sr-only"
            id="document-file"
          />
          <span className="material-symbols-outlined text-[40px] text-tecnia-primary dark:text-orange-300" aria-hidden="true">cloud_upload</span>
          <h3 className="mt-2 text-xl font-bold">Trascina qui i file</h3>
          <p className="my-2 text-sm text-tecnia-muted dark:text-slate-400">oppure</p>
          <label htmlFor="document-file" className="primary-button cursor-pointer">Scegli dal computer</label>
          <p className="mt-3 text-xs text-tecnia-muted dark:text-slate-400">PDF, Excel, CSV, TXT o SQL · fino a 25 MB ciascuno</p>
        </div>
        )}

        {items.length > 0 && (
          <div className="mt-4 rounded-xl border border-orange-200 bg-orange-50/60 p-3 dark:border-orange-900 dark:bg-orange-950/20">
            <ul className="divide-y divide-tecnia-line/40" aria-label="File da caricare">
              {items.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center gap-3 py-2" data-status={item.status}>
                  <span className={`material-symbols-outlined text-[20px] ${item.status === 'done' ? 'text-tecnia-ok' : item.status === 'error' ? 'text-red-700 dark:text-red-300' : 'text-tecnia-primary'} ${item.status === 'uploading' ? 'animate-spin' : ''}`} aria-hidden="true">{STATUS_ICON[item.status]}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.file.name}</p>
                    <p className="text-xs text-tecnia-muted">
                      {formatSize(item.file.size)} · {STATUS_LABEL[item.status]}
                      {item.status === 'waiting' && ` (${item.attempt} di ${MAX_RETRIES})`}
                      {item.status === 'error' && item.error ? ` · ${item.error}` : ''}
                    </p>
                  </div>
                  {item.status === 'error' && <button type="button" onClick={() => retryItem(item)} disabled={uploading} className="secondary-button !min-h-9 !px-3" aria-label={`Riprova a caricare ${item.file.name}`}>Riprova</button>}
                  {(item.status === 'queued' || item.status === 'error') && <button type="button" onClick={() => removeItem(item.id)} className="rounded-lg p-2 text-tecnia-muted hover:bg-orange-50 dark:hover:bg-slate-800" aria-label={`Togli ${item.file.name} dall'elenco`}><span className="material-symbols-outlined text-[18px]" aria-hidden="true">close</span></button>}
                </li>
              ))}
            </ul>
            {pending.length > 0 && (
              <div className="mt-3 flex justify-end">
                <button type="button" onClick={handleUpload} disabled={uploading} className="primary-button min-h-10 px-4">
                  {uploading ? 'Caricamento…' : 'Carica file'}
                </button>
              </div>
            )}
          </div>
        )}

        <div aria-live="polite">
          {error && <p role="alert" className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
          {success && <p className="mt-3 flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"><span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span>{success}</p>}
        </div>

        {documents.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-semibold">File disponibili</h3>
            <ul className="grid gap-2 sm:grid-cols-2">
              {documents.map((document) => (
                <li key={document.id} className="flex min-w-0 items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-[10px] font-black uppercase text-slate-600 dark:bg-slate-800 dark:text-slate-300">{document.file_type}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium" title={document.filename}>{document.filename}</span>
                    {document.provenance?.method && <span className="block truncate text-[10px] text-slate-500" title={document.provenance.sha256 || undefined}>Origine: {document.provenance.method}{document.provenance.sha256 ? ` · SHA-256 ${document.provenance.sha256.slice(0, 8)}…` : ''}</span>}
                  </span>
                  <span className="tag text-tecnia-ok dark:text-emerald-300">Letto</span>
                  {!readOnly && (
                    <button type="button" onClick={() => handleDelete(document)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30" aria-label={`Rimuovi ${document.filename}`} title="Rimuovi file">
                      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">delete</span>
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
