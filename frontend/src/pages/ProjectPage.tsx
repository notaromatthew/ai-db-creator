import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { cancelJob, createJob, setProjectDialect } from '@/api/projects'
import { useConfig } from '@/config/AppConfig'
import SchemaViewer from '@/components/SchemaViewer'
import SchemaDiagram from '@/components/SchemaDiagram'
import DataViewer from '@/components/DataViewer'
import DocumentUploader from '@/components/DocumentUploader'
import SchemaChat from '@/components/SchemaChat'
import QueryBuilder from '@/components/QueryBuilder'
import BackupManager from '@/components/BackupManager'
import Survey from '@/components/Survey'
import OperationHistory from '@/components/OperationHistory'
import ShareDialog from '@/components/ShareDialog'
import { downloadScript } from '@/components/ExportButton'
import Stepper from '@/components/flow/Stepper'
import ActionBar from '@/components/flow/ActionBar'
import ExportPanel from '@/components/flow/ExportPanel'
import GenerationProgress, { useSimulatedProgress } from '@/components/flow/GenerationProgress'
import { dialectLabel, type Dialect } from '@/components/flow/DialectPicker'
import JobProgress from '@/components/project/JobProgress'
import OcrNotice from '@/components/project/OcrNotice'
import QueryHistoryList from '@/components/project/QueryHistoryList'
import SchemaStatusBadge from '@/components/project/SchemaStatusBadge'
import SchemaVersionsPanel from '@/components/project/SchemaVersionsPanel'
import { isActive, useProjectJobs } from '@/components/project/useProjectJobs'
import type { QueryHistoryItem } from '@/types'

const READ_ONLY_NOTE = 'Hai accesso in sola lettura.'
const GEN_MAX_AGE_MS = 10 * 60 * 1000
const RECENT_JOB_MS = 30 * 60 * 1000
const AUTOSAVE_MS = 1500

const isRecent = (iso?: string) => {
  const t = iso ? Date.parse(iso) : NaN
  return Number.isFinite(t) && Date.now() - t < RECENT_JOB_MS
}

const store = {
  get(key: string): string | null {
    try { return window.localStorage.getItem(key) } catch { return null }
  },
  set(key: string, value: string) {
    try { window.localStorage.setItem(key, value) } catch { /* non disponibile */ }
  },
  remove(key: string) {
    try { window.localStorage.removeItem(key) } catch { /* non disponibile */ }
  },
}

function readGenerationStart(id: string): number | null {
  const raw = store.get(`aidb:gen:${id}`)
  const ts = raw ? Number(raw) : NaN
  return Number.isFinite(ts) && Date.now() - ts < GEN_MAX_AGE_MS ? ts : null
}

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const projectId = id!
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { config } = useConfig()
  const research = !!config.research_mode

  const [chosen, setChosen] = useState<number | null>(null)
  const [finalized, setFinalized] = useState(() => store.get(`aidb:final:${projectId}`) === '1')
  const [genStartedAt, setGenStartedAt] = useState<number | null>(() => readGenerationStart(projectId))
  const [genError, setGenError] = useState('')
  const [description, setDescription] = useState('')
  const [schemaView, setSchemaView] = useState<'diagram' | 'tables'>('diagram')
  const [dbView, setDbView] = useState<'diagram' | 'sql'>('diagram')
  const [dialect, setDialect] = useState<Dialect>('postgresql')
  const [queryOpen, setQueryOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [populateMessage, setPopulateMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [exportError, setExportError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [importDialect, setImportDialect] = useState('sqlite')
  const sqlInputRef = useRef<HTMLInputElement>(null)
  const [queryPrefill, setQueryPrefill] = useState<{ question?: string | null; sql?: string | null; source?: string; nonce: number } | null>(null)
  const [dismissedJobs, setDismissedJobs] = useState<string[]>([])
  const dialectInit = useRef(false)
  const seenActive = useRef<Set<string>>(new Set())

  const { data: project, isError: projectFailed } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`),
    enabled: !!id,
  })

  useEffect(() => {
    if (project?.target_dialect && !dialectInit.current) {
      dialectInit.current = true
      setDialect(project.target_dialect as Dialect)
    }
  }, [project?.target_dialect])

  const role: 'owner' | 'editor' | 'viewer' = project?.my_role ?? 'viewer'
  const canEdit = role !== 'viewer'

  const generationPolling = genStartedAt !== null
  const { data: schema } = useQuery({
    queryKey: ['schema', projectId],
    queryFn: () => api.get(`/projects/${projectId}/schema`),
    enabled: !!id,
    refetchInterval: generationPolling ? 4000 : false,
  })

  const { data: documents = [] } = useQuery<any[]>({
    queryKey: ['documents', projectId],
    queryFn: () => api.get(`/projects/${projectId}/documents`),
    enabled: !!id,
  })

  const { data: stats } = useQuery({
    queryKey: ['stats', projectId],
    queryFn: () => api.get(`/projects/${projectId}/data/stats`),
    enabled: !!id,
  })

  const { data: interactions = [] } = useQuery<any[]>({
    queryKey: ['interactions', projectId],
    queryFn: () => api.get(`/projects/${projectId}/interactions`),
    enabled: !!id && research,
  })

  const { jobs, activeJob, latest } = useProjectJobs(projectId, !!id && !research)
  const schemaJob = research ? undefined : activeJob('schema')
  const dataJob = research ? undefined : activeJob('dati')

  const hasSchema = !!schema && schema.tables?.length > 0
  const hasData = !!stats && Object.values(stats).some((v: any) => v > 0)
  const isFinal = finalized || hasData || !!project?.schema_finalized_at
  const docIds = documents.map((d: any) => d.id)
  const latestSchemaEvent = research
    ? [...interactions].reverse().find((e: any) => e.event_type === 'schema_generated' || e.event_type === 'schema_updated')
    : null

  const clearGeneration = () => {
    store.remove(`aidb:gen:${projectId}`)
    setGenStartedAt(null)
  }

  const genMut = useMutation({
    mutationFn: () => {
      const prompt = description.trim() || project?.prompt || 'Crea lo schema del database a partire dai documenti caricati.'
      return api.post(`/projects/${projectId}/generate`, { prompt, document_ids: docIds })
    },
    onMutate: () => {
      const now = Date.now()
      store.set(`aidb:gen:${projectId}`, String(now))
      setGenStartedAt(now)
      setGenError('')
      setChosen(null)
    },
    onSuccess: () => {
      clearGeneration()
      queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
      queryClient.invalidateQueries({ queryKey: ['interactions', projectId] })
      queryClient.invalidateQueries({ queryKey: ['chat-history', projectId] })
    },
    onError: (err: any) => {
      clearGeneration()
      setGenError(err?.message || 'Non è stato possibile generare lo schema.')
    },
  })

  const refreshAll = () => {
    for (const key of ['schema', 'project', 'stats', 'interactions', 'chat-history', 'schema-versions', 'data', 'jobs']) {
      queryClient.invalidateQueries({ queryKey: [key, projectId] })
    }
  }

  const startSchemaJob = useMutation({
    mutationFn: () => {
      const prompt = description.trim() || project?.prompt || 'Crea lo schema del database a partire dai documenti caricati.'
      return createJob(projectId, { kind: 'schema', prompt, document_ids: docIds })
    },
    onMutate: () => {
      setGenError('')
      setChosen(null)
      const previous = latest('schema')
      if (previous) setDismissedJobs((d) => [...d, previous.id])
    },
    onSuccess: refreshAll,
    onError: (err: any) => setGenError(err?.message || 'Non è stato possibile avviare la generazione.'),
  })

  const startGeneration = () => (research ? genMut.mutate() : startSchemaJob.mutate())

  const startDataJob = useMutation({
    mutationFn: async (reset: boolean) => {
      if (reset) await api.post(`/projects/${projectId}/reset-data`, {})
      return createJob(projectId, { kind: 'dati', document_ids: docIds })
    },
    onMutate: () => {
      setPopulateMessage(null)
      const previous = latest('dati')
      if (previous) setDismissedJobs((d) => [...d, previous.id])
    },
    onSuccess: refreshAll,
    onError: (err: any) => setPopulateMessage({ text: err?.message || 'Non è stato possibile avviare l\'inserimento dei dati.', isError: true }),
  })

  const cancelMut = useMutation({
    mutationFn: (jobId: string) => cancelJob(projectId, jobId),
    onSettled: refreshAll,
  })

  // Quando un lavoro seguito finisce (anche dopo una ripresa), aggiorna i dati e annuncia l'esito.
  const activeKey = jobs.filter(isActive).map((j) => j.id).join(',')
  useEffect(() => {
    const now = new Set(activeKey ? activeKey.split(',') : [])
    const finished = [...seenActive.current].filter((jid) => !now.has(jid))
    seenActive.current = now
    if (finished.length === 0) return
    refreshAll()
    for (const job of jobs.filter((j) => finished.includes(j.id) && j.kind === 'dati')) {
      if (job.status === 'done') {
        const parts = Object.entries(job.result?.tables ?? {}).map(([table, info]: [string, any]) => `${table}: +${info.inserted ?? 0}${info.skipped ? ` (${info.skipped} ignorati)` : ''}`)
        setPopulateMessage({ text: parts.length ? parts.join(', ') : 'Non è stato inserito nessun dato.', isError: false })
        store.set(`aidb:final:${projectId}`, '1')
        setFinalized(true)
      } else if (job.status === 'failed') setPopulateMessage({ text: job.error || 'Non è stato possibile inserire i dati.', isError: true })
      else if (job.status === 'cancelled') setPopulateMessage({ text: 'Hai annullato l\'inserimento dei dati.', isError: false })
    }
  }, [activeKey]) // eslint-disable-line react-hooks/exhaustive-deps

  const lastSchemaJob = latest('schema')
  const schemaJobError = !hasSchema && lastSchemaJob?.status === 'failed' && isRecent(lastSchemaJob.updated_at) && !dismissedJobs.includes(lastSchemaJob.id)
    ? (lastSchemaJob.error || 'Non è stato possibile generare lo schema.') : ''

  const generating = genMut.isPending || (!hasSchema && genStartedAt !== null) || !!schemaJob || startSchemaJob.isPending
  const simulated = useSimulatedProgress(generating && !schemaJob, genStartedAt)
  const progress = schemaJob ? schemaJob.progress : simulated

  // Fine della generazione ripresa dopo un ricaricamento, o scadenza di un avvio troppo vecchio.
  useEffect(() => {
    if (genMut.isPending || genStartedAt === null) return
    if (hasSchema) clearGeneration()
    else if (Date.now() - genStartedAt > GEN_MAX_AGE_MS) {
      clearGeneration()
      setGenError('La generazione sta richiedendo più del previsto. Riprova.')
    }
  }, [hasSchema, genStartedAt, schema, genMut.isPending]) // eslint-disable-line react-hooks/exhaustive-deps

  const populateMut = useMutation({
    mutationFn: async (reset?: boolean) => {
      if (reset === true) await api.post(`/projects/${projectId}/reset-data`, {})
      return api.post(`/projects/${projectId}/populate`, { document_ids: docIds })
    },
    onSuccess: (data: any) => {
      const parts: string[] = []
      for (const [table, info] of Object.entries(data || {})) {
        const r = info as any
        const method = r.provenance?.method
        const confidence = research && r.provenance && r.provenance.confidence == null ? ', confidenza non calibrata' : ''
        parts.push(`${table}: +${r.inserted}${r.skipped ? ` (${r.skipped} ignorati)` : ''}${research && method ? ` · ${method}${confidence}` : ''}`)
      }
      setPopulateMessage({ text: parts.length ? parts.join(', ') : 'Non è stato inserito nessun dato.', isError: false })
      store.set(`aidb:final:${projectId}`, '1')
      setFinalized(true)
      queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
      queryClient.invalidateQueries({ queryKey: ['data', projectId] })
    },
    onError: (err: any) => setPopulateMessage({ text: err?.message || 'Non è stato possibile inserire i dati.', isError: true }),
  })

  const populating = populateMut.isPending || startDataJob.isPending || !!dataJob
  const runData = (reset: boolean) => (research ? populateMut.mutate(reset) : startDataJob.mutate(reset))

  const importSqlMut = useMutation({
    mutationFn: ({ file, dialect: d }: { file: File; dialect: string }) => {
      const form = new FormData()
      form.append('file', file)
      return api.postFile(`/projects/${projectId}/import-sql?dialect=${d}`, form)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
    },
    onError: (err: any) => alert('Importazione non riuscita: ' + (err?.message || 'errore sconosciuto')),
  })

  const { data: ddl } = useQuery({
    queryKey: ['ddl', projectId, JSON.stringify(schema ?? null)],
    queryFn: () => api.get(`/projects/${projectId}/export?format=sql`),
    enabled: !!id && hasSchema && dbView === 'sql',
  })

  // ---- Passo corrente: dedotto dallo stato del progetto, modificabile con la barra dei passi ----
  const reachable = hasSchema ? (isFinal ? 4 : 3) : generating ? 2 : 1
  const defaultStep = generating ? 2 : hasSchema ? (isFinal ? 4 : 2) : 1
  const step = generating ? 2 : Math.min(Math.max(chosen ?? defaultStep, 1), reachable)

  const changeDialect = (d: Dialect) => {
    setDialect(d)
    if (canEdit) setProjectDialect(projectId, d).catch(() => { /* la scelta vale comunque per questo download */ })
  }

  const finalize = () => {
    if (!window.confirm('Dopo questo passo la chat si chiude e lo schema non si modifica più. Vuoi continuare?')) return
    store.set(`aidb:final:${projectId}`, '1')
    setFinalized(true)
    setChosen(4)
    api.post(`/projects/${projectId}/finalize`, {}).then(() => queryClient.invalidateQueries({ queryKey: ['project', projectId] })).catch(() => {})
  }

  const regenerateSchema = () => {
    if (window.confirm('Rigenerare lo schema? Le modifiche fatte finora allo schema andranno perse.')) startGeneration()
  }

  const regenerateData = () => {
    setPopulateMessage(null)
    if (!hasData || window.confirm('Rigenerare i dati? Le righe attuali vengono sostituite; prima viene salvata una copia di sicurezza.')) runData(hasData)
  }

  const handleDownload = async () => {
    setExporting(true)
    setExportError('')
    try {
      await downloadScript(projectId, dialect)
    } catch (e: any) {
      setExportError(e?.message || 'Non è stato possibile preparare lo script.')
    } finally {
      setExporting(false)
    }
  }

  const onSqlFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) importSqlMut.mutate({ file, dialect: importDialect })
    e.target.value = ''
  }

  if (projectFailed) return <div className="surface p-8 text-center" role="alert">Non trovo questo progetto, oppure non hai accesso. <Link to="/app" className="font-semibold underline">Torna ai progetti</Link></div>
  if (!project) return <div className="surface p-8 text-center text-slate-500" role="status">Caricamento del progetto…</div>

  const tableCount = schema?.tables?.length ?? 0
  const relCount = schema?.relationships?.length ?? 0

  const tabs = (value: string, onChange: (v: any) => void, items: { id: string; label: string; icon: string }[], label: string) => (
    <div className="inline-flex gap-1 rounded-full border border-tecnia-line bg-white/60 p-1 dark:border-slate-600 dark:bg-slate-800/60" role="tablist" aria-label={label}>
      {items.map((t) => (
        <button key={t.id} type="button" role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={`flex min-h-9 items-center gap-1.5 rounded-full px-4 font-headline text-sm font-semibold transition ${value === t.id ? 'bg-orange-500/15 text-tecnia-primary dark:text-orange-300' : 'text-tecnia-muted hover:text-tecnia-ink dark:text-slate-400'}`}>
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{t.icon}</span>{t.label}
        </button>
      ))}
    </div>
  )

  // ---- Contenuto e barra azioni per passo ----
  let body: React.ReactNode = null
  let bar: React.ComponentProps<typeof ActionBar>

  if (generating) {
    body = <GenerationProgress progress={progress} onCancel={schemaJob ? () => cancelMut.mutate(schemaJob.id) : undefined} cancelling={cancelMut.isPending} />
    bar = { step: 2, info: 'Generazione in corso. Puoi chiudere la pagina: la ritrovi nell\'elenco progetti.' }
  } else if (step === 1) {
    body = (
      <div className="mx-auto max-w-3xl space-y-5">
        <div>
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Da cosa vuoi partire?</h2>
          <p className="mt-1.5 text-sm text-tecnia-muted dark:text-slate-400">Carica uno o più documenti. Bastano pochi file.</p>
        </div>
        <DocumentUploader projectId={projectId} readOnly={!canEdit} onUpload={() => queryClient.invalidateQueries({ queryKey: ['documents', projectId] })} />
        <OcrNotice documents={documents} />
        {canEdit && (
          <div>
            <label className="mb-1.5 block font-headline text-sm font-semibold" htmlFor="project-description">
              Cosa deve contenere il database? <span className="font-normal text-tecnia-muted dark:text-slate-400">(facoltativo)</span>
            </label>
            <input id="project-description" className="field" value={description} onChange={(e) => setDescription(e.target.value)} placeholder={project.prompt || 'Es. Voglio tenere traccia di clienti, ordini e prodotti'} />
          </div>
        )}
        {(genError || schemaJobError) && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{genError || schemaJobError}</p>}
        {canEdit && (
          <details className="surface p-4">
            <summary className="cursor-pointer text-sm font-semibold">Hai già uno script SQL? Importalo</summary>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <label className="text-sm" htmlFor="import-dialect">Formato</label>
              <select id="import-dialect" className="field w-auto" value={importDialect} onChange={(e) => setImportDialect(e.target.value)}>
                <option value="sqlite">SQLite</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL e MariaDB</option>
                <option value="mssql">SQL Server</option>
              </select>
              <input ref={sqlInputRef} type="file" accept=".sql" className="hidden" onChange={onSqlFile} />
              <button type="button" className="secondary-button" disabled={importSqlMut.isPending} onClick={() => sqlInputRef.current?.click()}>
                {importSqlMut.isPending ? 'Importazione…' : 'Scegli il file .sql'}
              </button>
            </div>
          </details>
        )}
        {canEdit && hasSchema && !isFinal && (
          <button type="button" className="secondary-button" onClick={regenerateSchema}>Rigenera lo schema da capo</button>
        )}
        <p className="text-sm text-tecnia-muted dark:text-slate-400">I tuoi file restano privati: li vedono solo le persone con cui condividi il progetto.</p>
      </div>
    )
    bar = {
      step: 1,
      info: hasSchema ? 'Lo schema è già pronto.' : documents.length > 0 ? `${documents.length} ${documents.length === 1 ? 'file letto' : 'file letti'}.` : 'Il pulsante si attiva appena un file è letto.',
      note: !canEdit ? READ_ONLY_NOTE : undefined,
      secondary: { label: 'Salva ed esci', onClick: () => navigate('/app') },
      primary: hasSchema
        ? { label: 'Continua', icon: 'arrow_forward', onClick: () => setChosen(2) }
        : { label: 'Genera lo schema', icon: 'auto_awesome', onClick: startGeneration, disabled: !canEdit || (documents.length === 0 && !description.trim()) },
    }
  } else if (step === 2) {
    body = (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <section className="min-w-0 space-y-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Controlla lo schema proposto</h2>
            <p className="mt-1.5 text-sm text-tecnia-muted dark:text-slate-400">
              L'IA ha trovato {tableCount} {tableCount === 1 ? 'tabella' : 'tabelle'} nei tuoi documenti. Cambia ciò che non va, poi conferma.
            </p>
          </div>
          {tabs(schemaView, setSchemaView, [{ id: 'diagram', label: 'Diagramma', icon: 'account_tree' }, { id: 'tables', label: 'Tabelle', icon: 'table_rows' }], 'Vista dello schema')}
          {schemaView === 'diagram' ? <SchemaDiagram schema={schema} /> : <SchemaViewer schema={schema} projectId={projectId} readOnly={!canEdit || isFinal} autosaveMs={AUTOSAVE_MS} />}
          <p className="text-xs text-tecnia-muted dark:text-slate-400">Un legame 1 : N è una relazione uno a molti. Chiedi all'IA a destra di cambiare qualcosa: il diagramma si aggiorna e approvi tu.</p>
          <SchemaVersionsPanel projectId={projectId} readOnly={!canEdit} />
        </section>
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <SchemaChat projectId={projectId} schema={schema} documentIds={docIds} locked={isFinal} readOnly={!canEdit} />
        </aside>
      </div>
    )
    bar = {
      step: 2,
      info: isFinal ? 'Schema definitivo.' : 'Schema in bozza: la chat resta attiva fino alla conferma.',
      back: { label: 'Indietro', onClick: () => setChosen(1) },
      primary: { label: 'Continua', icon: 'arrow_forward', onClick: () => setChosen(3) },
    }
  } else if (step === 3) {
    body = (
      <div className="space-y-5">
        <div className="glass flex items-start gap-3 p-5">
          <span className="material-symbols-outlined text-tecnia-ok" aria-hidden="true" style={{ fontVariationSettings: "'FILL' 1" }}>{isFinal ? 'lock' : 'edit_note'}</span>
          <div>
            <h2 className="text-xl font-bold">{isFinal ? 'Database pronto, schema definitivo' : 'Database pronto, schema ancora in bozza'}</h2>
            <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">
              {tableCount} {tableCount === 1 ? 'tabella' : 'tabelle'} e {relCount} {relCount === 1 ? 'relazione' : 'relazioni'}{hasData ? '.' : ', per ora vuote.'}{' '}
              {isFinal ? 'Si passa ai dati.' : 'Quando sei soddisfatto, rendi lo schema definitivo: poi si passa ai dati.'}
            </p>
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section className="min-w-0 space-y-4">
            {tabs(dbView, setDbView, [{ id: 'diagram', label: 'Diagramma', icon: 'account_tree' }, { id: 'sql', label: 'Istruzioni SQL', icon: 'code' }], 'Vista del database')}
            {dbView === 'diagram'
              ? <SchemaDiagram schema={schema} />
              : <pre className="max-h-[560px] overflow-auto rounded-2xl border border-tecnia-line bg-white/80 p-4 font-mono text-xs dark:border-slate-700 dark:bg-slate-900" aria-label="Istruzioni SQL dello schema">{ddl?.content ?? 'Preparo le istruzioni…'}</pre>}
            <SchemaVersionsPanel projectId={projectId} readOnly={!canEdit} />
          </section>
          <aside className="lg:sticky lg:top-4 lg:self-start">
            <SchemaChat projectId={projectId} schema={schema} documentIds={docIds} locked={isFinal} readOnly={!canEdit} />
          </aside>
        </div>
      </div>
    )
    bar = {
      step: 3,
      info: isFinal ? 'Schema definitivo: la chat è chiusa.' : 'Schema in bozza: la chat resta attiva fino alla conferma.',
      note: !canEdit && !isFinal ? READ_ONLY_NOTE : undefined,
      back: { label: isFinal ? 'Indietro' : 'Torna alla revisione', onClick: () => setChosen(2) },
      primary: isFinal
        ? { label: 'Continua', icon: 'arrow_forward', onClick: () => setChosen(4) }
        : { label: 'Rendi definitivo e continua', icon: 'arrow_forward', onClick: finalize, disabled: !canEdit },
    }
  } else {
    body = (
      <div className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">{hasData ? 'Dati generati' : 'Il database è ancora vuoto'}</h2>
            <p className="mt-1.5 text-sm text-tecnia-muted dark:text-slate-400">
              {hasData ? 'Controlla un\'anteprima. Se non ti convincono, rigenera.' : canEdit ? 'Premi "Genera i dati": li ricavo dai tuoi documenti e li inserisco nelle tabelle.' : 'Nessun dato è stato ancora generato.'}
            </p>
          </div>
          {hasData && <span className="tag text-tecnia-ok dark:text-emerald-300">Coerenti con lo schema</span>}
        </div>
        {dataJob && <JobProgress job={dataJob} title="Sto inserendo i dati" onCancel={() => cancelMut.mutate(dataJob.id)} cancelling={cancelMut.isPending} />}
        {populateMessage && <p role={populateMessage.isError ? 'alert' : 'status'} aria-live="polite" className={`text-sm ${populateMessage.isError ? 'text-red-600' : 'text-emerald-700 dark:text-emerald-300'}`}>{populateMessage.text}</p>}
        {hasData && <DataViewer projectId={projectId} schema={schema} autoLoad />}
        {hasData && (
          <ExportPanel
            projectId={projectId}
            schema={schema}
            dialect={dialect}
            onDialectChange={changeDialect}
            queryOpen={queryOpen}
            onToggleQuery={() => setQueryOpen((v) => !v)}
            onRegenerate={canEdit ? regenerateData : undefined}
            regenerating={populating}
          />
        )}
        {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        {hasData && queryOpen && (
          <>
            <QueryHistoryList projectId={projectId} onPick={(item: QueryHistoryItem) => setQueryPrefill({ question: item.question, sql: item.sql, source: item.source, nonce: Date.now() })} />
            <QueryBuilder
              projectId={projectId}
              schema={schema}
              prefill={queryPrefill}
              onActivity={() => queryClient.invalidateQueries({ queryKey: ['queries', projectId] })}
              onDataChange={() => queryClient.invalidateQueries({ queryKey: ['stats', projectId] })}
            />
          </>
        )}
        {canEdit && <BackupManager projectId={projectId} />}
        {research && <OperationHistory projectId={projectId} />}
        {research && <Survey projectId={projectId} />}
      </div>
    )
    bar = {
      step: 4,
      info: hasData ? `Scegli il database di destinazione e scarica lo script.` : 'Genera i dati di prova per poi esportarli.',
      note: !canEdit && !hasData ? READ_ONLY_NOTE : undefined,
      back: { label: 'Indietro', onClick: () => setChosen(3) },
      primary: hasData
        ? { label: `Scarica lo script per ${dialectLabel(dialect)}`, icon: 'download', onClick: handleDownload, loading: exporting }
        : { label: 'Genera i dati', icon: 'auto_awesome', onClick: () => runData(false), loading: populating, disabled: !canEdit },
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link to="/app" className="mb-2 inline-flex items-center gap-1 rounded-lg text-sm font-medium text-tecnia-muted hover:text-tecnia-primary dark:text-slate-400">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">arrow_back</span>Progetti
          </Link>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{project.name}</h1>
          {hasSchema && <div className="mt-2"><SchemaStatusBadge finalized={isFinal} version={project.schema_version} /></div>}
          {latestSchemaEvent && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Provenienza schema: {latestSchemaEvent.event_type === 'schema_updated' ? 'revisione umana' : `${latestSchemaEvent.data?.provider || 'IA'} · ${latestSchemaEvent.data?.model || 'modello non disponibile'}`} · run {String(latestSchemaEvent.run_id).slice(0, 8)} · confidenza non calibrata
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!canEdit && <span className="tag text-amber-700 dark:text-amber-300">Sola lettura</span>}
          {role === 'owner' && (
            <button type="button" className="secondary-button" onClick={() => setShareOpen(true)}>
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">group_add</span>Condividi
            </button>
          )}
        </div>
      </header>

      <Stepper current={step} reachable={reachable} onSelect={setChosen} />

      {!canEdit && (
        <p className="mb-5 flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-200" role="note">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span>
          {READ_ONLY_NOTE} Puoi guardare tutto, ma non modificare.
        </p>
      )}

      {body}

      <ActionBar {...bar} />

      {role === 'owner' && <ShareDialog projectId={projectId} open={shareOpen} onClose={() => setShareOpen(false)} />}
    </div>
  )
}
