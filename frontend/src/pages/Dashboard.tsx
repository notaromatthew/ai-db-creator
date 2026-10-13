import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Project } from '@/types'
import { useAuth } from '@/context/KeycloakContext'
import { ProjectWizardModal } from '@/components/ProjectWizardModal'

const ROLE_LABEL: Record<string, string> = { owner: 'Proprietario', editor: 'Editor', viewer: 'Lettore' }
const ROLE_COLOR: Record<string, string> = { owner: 'text-tecnia-primary', editor: 'text-tecnia-magentaDeep', viewer: 'text-tecnia-muted' }
const STATUS: Record<string, { label: string; color: string }> = {
  not_started: { label: 'Da iniziare', color: 'text-tecnia-muted' },
  schema_review: { label: 'Schema da rivedere', color: 'text-amber-700' },
  data_ready: { label: 'Dati pronti', color: 'text-tecnia-ok' },
}

function ProjectCard({ project, onDelete, onLeave, busy }: {
  project: Project
  onDelete: (p: Project) => void
  onLeave: (p: Project) => void
  busy: boolean
}) {
  const role = project.my_role ?? 'owner'
  const status = STATUS[project.status ?? 'not_started'] ?? STATUS.not_started
  const step = project.step ?? 1
  const docs = project.document_count ?? 0
  return (
    <article className="glass group relative flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:border-orange-300">
      <Link to={`/app/projects/${project.id}`} className="flex flex-col gap-3 rounded-xl" aria-label={`Apri ${project.name}`}>
        <div className="flex items-start justify-between gap-3">
          <h3 className="truncate text-lg font-bold group-hover:text-tecnia-primary">{project.name}</h3>
          <span className={`tag shrink-0 ${status.color}`}>{status.label}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" role="progressbar" aria-valuemin={0} aria-valuemax={4} aria-valuenow={step} aria-label={`Passo ${step} di 4`}>
          <i className="block h-full bg-gradient-to-r from-[#ff6b00] to-[#fe3ac6]" style={{ width: `${(step / 4) * 100}%` }} />
        </div>
        <p className="text-[13px] text-tecnia-muted dark:text-slate-400">
          Passo {step} di 4 · {docs} {docs === 1 ? 'documento' : 'documenti'}
          {project.owner_name && role !== 'owner' ? ` · di ${project.owner_name}` : ''}
        </p>
      </Link>
      <div className="flex items-center justify-between gap-2">
        <span className={`tag ${ROLE_COLOR[role]}`}>{ROLE_LABEL[role]}</span>
        {role === 'owner' ? (
          <button type="button" onClick={() => onDelete(project)} disabled={busy} className="flex min-h-9 items-center gap-1 rounded-full px-3 text-xs font-semibold text-slate-500 hover:bg-red-50 hover:text-red-700" aria-label={`Elimina ${project.name}`}>
            <span className="material-symbols-outlined !text-[18px]">delete</span>Elimina
          </button>
        ) : (
          <button type="button" onClick={() => onLeave(project)} disabled={busy} className="flex min-h-9 items-center gap-1 rounded-full px-3 text-xs font-semibold text-slate-500 hover:bg-orange-50 hover:text-tecnia-primary" aria-label={`Lascia il progetto ${project.name}`}>
            <span className="material-symbols-outlined !text-[18px]">logout</span>Lascia il progetto
          </button>
        )}
      </div>
    </article>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { username } = useAuth()
  const [error, setError] = useState('')
  const [isNewOpen, setIsNewOpen] = useState(false)

  const { data: projects, isLoading, isError } = useQuery<Project[]>({ queryKey: ['projects'], queryFn: () => api.get('/projects') })

  const createMut = useMutation({
    mutationFn: (data: { name: string; prompt: string }) => api.post('/projects', data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setIsNewOpen(false)
      navigate(`/app/projects/${result.id}`)
    },
    onError: (caught: any) => setError(caught?.message || 'Non siamo riusciti a creare il progetto. Riprova tra poco.'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })
  const leaveMut = useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}/membership`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })

  const { mine, shared } = useMemo(() => {
    const list = projects ?? []
    return {
      mine: list.filter((p) => (p.my_role ?? 'owner') === 'owner'),
      shared: list.filter((p) => (p.my_role ?? 'owner') !== 'owner'),
    }
  }, [projects])

  const next = mine.find((p) => p.status === 'schema_review')

  const handleDelete = (project: Project) => {
    if (window.confirm(`Eliminare definitivamente “${project.name}”? Schema, dati e documenti andranno persi.`)) deleteMut.mutate(project.id)
  }
  const handleLeave = (project: Project) => {
    if (window.confirm(`Vuoi lasciare “${project.name}”? Non lo vedrai più, a meno di un nuovo invito.`)) leaveMut.mutate(project.id)
  }
  const busy = deleteMut.isPending || leaveMut.isPending
  const first = username && username !== 'Ospite' ? username.split(/[\s@]/)[0] : ''

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{first ? `Ciao ${first}` : 'I tuoi progetti'}</h1>
          <p className="mt-1.5 text-base text-tecnia-muted dark:text-slate-400">Riparti da dove eri, oppure inizia un nuovo database.</p>
        </div>
        <button type="button" onClick={() => { setError(''); setIsNewOpen(true) }} className="primary-button">
          <span className="material-symbols-outlined">add</span>Nuovo progetto
        </button>
      </header>

      {next && (
        <section className="glass flex flex-wrap items-center gap-5 border-orange-300 p-6" aria-label="Prossimo passo">
          <span className="material-symbols-outlined !text-[32px] text-tecnia-primary">play_circle</span>
          <div className="min-w-[220px] flex-1">
            <h2 className="text-lg font-bold">Prossimo passo: controlla lo schema di “{next.name}”</h2>
            <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">L'IA ha proposto {next.table_count ?? 0} {next.table_count === 1 ? 'tabella' : 'tabelle'}. Servono circa 2 minuti.</p>
          </div>
          <Link to={`/app/projects/${next.id}`} className="primary-button">Continua<span className="material-symbols-outlined">arrow_forward</span></Link>
        </section>
      )}

      {isLoading ? (
        <div className="glass p-8 text-center text-tecnia-muted" role="status">Sto caricando i tuoi progetti…</div>
      ) : isError ? (
        <div className="glass p-8 text-center" role="alert">
          <p className="font-semibold">Non riusciamo a caricare i progetti.</p>
          <p className="mt-1 text-sm text-tecnia-muted">Controlla la connessione e ricarica la pagina.</p>
        </div>
      ) : (
        <>
          <section aria-labelledby="mine-title" className="flex flex-col gap-3.5">
            <h2 id="mine-title" className="text-xl font-bold">I tuoi progetti</h2>
            {mine.length === 0 ? (
              <div className="glass border-dashed p-10 text-center">
                <span className="material-symbols-outlined !text-[36px] text-tecnia-primary">upload_file</span>
                <h3 className="mt-2 text-lg font-bold">Non hai ancora progetti</h3>
                <p className="mx-auto mt-1 max-w-md text-sm text-tecnia-muted dark:text-slate-400">Crea il primo: descrivi cosa ti serve, carica i tuoi documenti e l'IA propone tabelle e relazioni.</p>
                <button type="button" onClick={() => { setError(''); setIsNewOpen(true) }} className="primary-button mt-5">Crea il primo progetto</button>
              </div>
            ) : (
              <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {mine.map((p) => <ProjectCard key={p.id} project={p} onDelete={handleDelete} onLeave={handleLeave} busy={busy} />)}
              </div>
            )}
          </section>

          {shared.length > 0 && (
            <section aria-labelledby="shared-title" className="flex flex-col gap-3.5">
              <h2 id="shared-title" className="text-xl font-bold">Condivisi con me</h2>
              <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {shared.map((p) => <ProjectCard key={p.id} project={p} onDelete={handleDelete} onLeave={handleLeave} busy={busy} />)}
              </div>
            </section>
          )}
        </>
      )}

      <ProjectWizardModal
        isOpen={isNewOpen}
        onClose={() => setIsNewOpen(false)}
        onCreateProject={(name, prompt) => { setError(''); createMut.mutate({ name, prompt }) }}
        busy={createMut.isPending}
        error={error}
      />
    </div>
  )
}
