import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { Project, NormalizedSchema } from '@/types'
import SchemaViewer from '@/components/SchemaViewer'
import SchemaDiagram from '@/components/SchemaDiagram'
import DataViewer from '@/components/DataViewer'
import DocumentUploader from '@/components/DocumentUploader'
import SchemaChat from '@/components/SchemaChat'
import QueryBuilder from '@/components/QueryBuilder'
import ExportButton from '@/components/ExportButton'
import BackupManager from '@/components/BackupManager'
import Survey from '@/components/Survey'
import GuidedWorkflow from '@/components/GuidedWorkflow'
import OperationHistory from '@/components/OperationHistory'
import { useState, useRef } from 'react'

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'schema' | 'data' | 'query'>('schema')
  const [showDiagram, setShowDiagram] = useState(false)
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const importDialects = ['sqlite', 'postgresql', 'mysql', 'mssql']
  const sqlInputRef = useRef<HTMLInputElement>(null)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.get(`/projects/${id}`),
    enabled: !!id,
  })

  const { data: schema } = useQuery({
    queryKey: ['schema', id],
    queryFn: () => api.get(`/projects/${id}/schema`),
    enabled: !!id,
  })

  const { data: documents } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => api.get(`/projects/${id}/documents`),
    enabled: !!id,
  })

  const { data: stats } = useQuery({
    queryKey: ['stats', id],
    queryFn: () => api.get(`/projects/${id}/data/stats`),
    enabled: !!id,
  })

  const { data: interactions = [] } = useQuery<any[]>({
    queryKey: ['interactions', id],
    queryFn: () => api.get(`/projects/${id}/interactions`),
    enabled: !!id,
  })

  const [populateMessage, setPopulateMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [quickPrompt, setQuickPrompt] = useState('')
  const [quickError, setQuickError] = useState('')

  const hasSchema = !!schema && schema.tables?.length > 0
  const hasData = stats && Object.values(stats).some((v: any) => v > 0)
  const latestSchemaEvent = [...interactions].reverse().find((event: any) => event.event_type === 'schema_generated' || event.event_type === 'schema_updated')

  const populateMut = useMutation({
    mutationFn: (docIds: string[]) => api.post(`/projects/${id}/populate`, { document_ids: docIds }),
    onSuccess: (data: any) => {
      const parts: string[] = []
      for (const [table, info] of Object.entries(data)) {
        const r = info as any
        const method = r.provenance?.method
        const confidence = r.provenance && r.provenance.confidence == null ? ', confidenza non calibrata' : ''
        parts.push(`${table}: +${r.inserted}${r.skipped ? ` (${r.skipped} ignorati)` : ''}${method ? ` · ${method}${confidence}` : ''}`)
      }
      setPopulateMessage({ text: parts.length ? parts.join(', ') : 'No data inserted', isError: false })
      queryClient.invalidateQueries({ queryKey: ['stats', id] })
      queryClient.invalidateQueries({ queryKey: ['data', id] })
    },
    onError: (err: any) => {
      setPopulateMessage({ text: err?.message || 'Non è stato possibile inserire i dati.', isError: true })
    },
  })

  const quickGenMut = useMutation({
    mutationFn: (prompt: string) => {
      const docIds = documents ? documents.map((d: any) => d.id) : []
      return api.post(`/projects/${id}/generate`, { prompt, document_ids: docIds })
    },
    onSuccess: () => {
      setQuickError('')
      setQuickPrompt('')
      queryClient.invalidateQueries({ queryKey: ['schema', id] })
      queryClient.invalidateQueries({ queryKey: ['interactions', id] })
    },
    onError: (err: any) => {
      setQuickError(err?.message || 'Non è stato possibile generare lo schema.')
    },
  })

  const importSqlMut = useMutation({
    mutationFn: ({ file, dialect }: { file: File; dialect: string }) => {
      const form = new FormData()
      form.append('file', file)
      return api.postFile(`/projects/${id}/import-sql?dialect=${dialect}`, form)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schema', id] })
      queryClient.invalidateQueries({ queryKey: ['project', id] })
      queryClient.invalidateQueries({ queryKey: ['stats', id] })
    },
    onError: (err: any) => {
      alert('Importazione non riuscita: ' + (err?.message || 'errore sconosciuto'))
    },
  })

  const handleImportSql = (dialect: string) => {
    const input = sqlInputRef.current
    if (!input) return
    input.dataset.dialect = dialect
    input.click()
  }

  const handleSqlFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const dialect = e.target.dataset.dialect || 'sqlite'
    importSqlMut.mutate({ file, dialect })
    e.target.value = ''
  }

  const handlePopulate = async () => {
    const docIds = documents ? documents.map((d: any) => d.id) : []
    setPopulateMessage(null)
    await populateMut.mutateAsync(docIds)
  }

  if (!project) return <div className="surface p-8 text-center text-slate-500" role="status">Caricamento del progetto…</div>

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <Link to="/" className="mb-3 inline-flex items-center gap-1 rounded-lg text-sm font-medium text-slate-500 hover:text-blue-700 dark:hover:text-blue-300">← Tutti i progetti</Link>
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Area di lavoro</p>
            <h1 className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">{project.name}</h1>
            {project.prompt && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500 dark:text-slate-400">{project.prompt}</p>}
            {latestSchemaEvent && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Provenienza schema: {latestSchemaEvent.event_type === 'schema_updated' ? 'revisione umana' : `${latestSchemaEvent.data?.provider || 'IA'} · ${latestSchemaEvent.data?.model || 'modello non disponibile'}`} · run {String(latestSchemaEvent.run_id).slice(0, 8)} · confidenza non calibrata
            </p>}
          </div>
          <span className={`w-fit rounded-full px-3 py-1 text-xs font-semibold ${hasData ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : hasSchema ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'}`}>
            {hasData ? 'Database pronto' : hasSchema ? 'Schema creato' : 'Configurazione iniziale'}
          </span>
        </div>
      </header>

      <GuidedWorkflow
        documentsCount={documents?.length || 0}
        hasSchema={hasSchema}
        hasData={hasData}
        onGoTo={(tab) => setActiveTab(tab as any)}
      />

      <nav className="mb-6 grid grid-cols-3 gap-1 rounded-xl bg-slate-200/70 p-1 dark:bg-slate-800" aria-label="Sezioni del progetto">
        {([['schema', 'Struttura'], ['data', 'Dati'], ['query', 'Interroga']] as const).map(([tab, label]) => {
          const disabled = tab !== 'schema' && !hasSchema
          return (
            <button key={tab} onClick={() => setActiveTab(tab)} disabled={disabled} title={disabled ? 'Crea prima lo schema del database' : undefined} className={`min-h-10 rounded-lg px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${activeTab === tab ? 'bg-white text-blue-700 shadow-sm dark:bg-slate-700 dark:text-blue-300' : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white'}`} aria-current={activeTab === tab ? 'page' : undefined}>
              {label}{disabled && <span className="ml-1.5 text-xs" aria-hidden="true">🔒</span>}
              {disabled && <span className="sr-only">, disponibile dopo la creazione dello schema</span>}
            </button>
          )
        })}
      </nav>

      <div className="mb-6">
        <DocumentUploader projectId={id!} onUpload={() => { queryClient.invalidateQueries({ queryKey: ['documents', id] }) }} />
      </div>

      {activeTab === 'schema' && (
        <div className="space-y-4">
          <SchemaChat projectId={id!} schema={schema || null} documentIds={documents ? documents.map((d: any) => d.id) : []} />

          <details className="surface p-4">
            <summary className="cursor-pointer text-sm font-semibold text-slate-600 dark:text-slate-300">Generazione rapida dello schema</summary>
            <p className="mt-2 text-xs text-slate-500">Descrivi in poche parole le informazioni da organizzare.</p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input value={quickPrompt} onChange={(e) => setQuickPrompt(e.target.value)} placeholder="Es. Clienti, ordini, prodotti e pagamenti…" className="field flex-1 text-sm" />
              <button onClick={() => quickGenMut.mutate(quickPrompt)} disabled={quickGenMut.isPending || !quickPrompt.trim()} className="primary-button text-sm">
                {quickGenMut.isPending ? 'Generazione…' : 'Genera schema'}
              </button>
            </div>
            {quickError && <p className="text-red-500 text-sm mt-1">{quickError}</p>}
          </details>

          {hasSchema && (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <button onClick={() => setShowDiagram(!showDiagram)} className="secondary-button min-h-9 px-3 text-sm">{showDiagram ? 'Vista tabelle' : 'Vista diagramma'}</button>
                <ExportButton projectId={id!} />
                <div className="relative inline-block">
                  <input ref={sqlInputRef} type="file" accept=".sql" className="hidden" onChange={handleSqlFileSelected} />
                  <button onClick={() => setImportDialogOpen(!importDialogOpen)} disabled={importSqlMut.isPending} className="px-3 py-1 bg-purple-600 text-white rounded text-sm disabled:opacity-50">
                    {importSqlMut.isPending ? 'Importazione…' : 'Importa SQL'}
                  </button>
                  {importDialogOpen && (
                    <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg z-10 min-w-40">
                      <div className="px-3 py-1 text-xs text-gray-500 uppercase tracking-wider">Formato SQL</div>
                      {importDialects.map(d => (
                        <button key={d} onClick={() => { setImportDialogOpen(false); handleImportSql(d) }} className="block w-full px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-left capitalize">{d}</button>
                      ))}
                    </div>
                  )}
                </div>
                <BackupManager projectId={id!} />
                <OperationHistory projectId={id!} />
                <button onClick={handlePopulate} className="bg-green-600 text-white px-4 py-1 rounded text-sm disabled:opacity-50" disabled={populateMut.isPending}>
                  {populateMut.isPending ? 'Inserimento…' : 'Popola le tabelle'}
                </button>
              </div>
              {populateMessage && <p className={`text-sm ${populateMessage.isError ? 'text-red-500' : 'text-green-500'}`}>{populateMessage.text}</p>}
              {showDiagram && <SchemaDiagram schema={schema} />}
              {!showDiagram && <SchemaViewer schema={schema} projectId={id!} />}
            </>
          )}
          {!hasSchema && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded p-4 text-sm text-yellow-800 dark:text-yellow-200">
              Carica uno o più documenti nella sezione qui sopra, poi usa l'assistente o la generazione rapida per creare lo schema del database.
            </div>
          )}
        </div>
      )}

      {activeTab === 'data' && hasSchema && <DataViewer projectId={id!} schema={schema} autoLoad />}
      {activeTab === 'query' && hasSchema && <QueryBuilder projectId={id!} schema={schema} onDataChange={() => queryClient.invalidateQueries({ queryKey: ['stats', id] })} />}

      <Survey projectId={id!} />
    </div>
  )
}
