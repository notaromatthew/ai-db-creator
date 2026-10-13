import { useRef, useState } from 'react'
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

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentUploader({ projectId, onUpload, readOnly = false }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: documents = [] } = useQuery<ProjectDocument[]>({
    queryKey: ['documents', projectId],
    queryFn: () => api.get(`/projects/${projectId}/documents`),
    enabled: !!projectId,
  })

  const selectFile = (nextFile?: File) => {
    setError('')
    setSuccess('')
    if (!nextFile) {
      setFile(null)
      return
    }
    const extension = nextFile.name.split('.').pop()?.toLowerCase() || ''
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setFile(null)
      setError('Formato non supportato. Usa PDF, Excel, CSV, TXT o SQL.')
      return
    }
    if (nextFile.size > MAX_FILE_SIZE) {
      setFile(null)
      setError('Il file supera il limite di 25 MB.')
      return
    }
    setFile(nextFile)
  }

  const refreshDocuments = async () => {
    await queryClient.invalidateQueries({ queryKey: ['documents', projectId] })
    onUpload()
  }

  const handleUpload = async () => {
    if (!file) return
    const uploadedName = file.name
    setUploading(true)
    setError('')
    setSuccess('')
    let baselineIds = new Set(documents.map((document) => document.id))
    try {
      const baseline: ProjectDocument[] = await api.get(`/projects/${projectId}/documents`)
      baselineIds = new Set(baseline.map((document) => document.id))
      await api.postFile(`/projects/${projectId}/documents`, file)
      await refreshDocuments()
      setSuccess(`“${uploadedName}” è pronto per essere usato.`)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
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
          setSuccess(`“${uploadedName}” è stato caricato correttamente.`)
          setFile(null)
          if (inputRef.current) inputRef.current.value = ''
          return
        }
      } catch {
        // Mantiene il messaggio originale se anche la verifica non è disponibile.
      }
      setError(uploadError?.message || 'Non è stato possibile caricare il file. Riprova.')
    } finally {
      setUploading(false)
    }
  }

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
            <p className="mb-1 text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Documenti di partenza</p>
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
          onDrop={(event) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]) }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.xls,.xlsx,.txt,.csv,.sql"
            onChange={(event) => selectFile(event.target.files?.[0])}
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

        {file && (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-blue-200 bg-blue-50 p-3 sm:flex-row sm:items-center dark:border-blue-800 dark:bg-blue-950/30">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{file.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{formatSize(file.size)} · pronto per il caricamento</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => selectFile()} disabled={uploading} className="secondary-button min-h-10 px-3">Annulla</button>
              <button type="button" onClick={handleUpload} disabled={uploading} className="primary-button min-h-10 px-4">
                {uploading ? 'Caricamento…' : 'Carica file'}
              </button>
            </div>
          </div>
        )}

        <div aria-live="polite">
          {error && <p role="alert" className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
          {success && <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">✓ {success}</p>}
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
