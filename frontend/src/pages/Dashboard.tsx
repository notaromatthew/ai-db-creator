import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Project } from '@/types'
import { useState } from 'react'
import { ProjectWizardModal } from '@/components/ProjectWizardModal'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState('')
  const [isWizardOpen, setIsWizardOpen] = useState(false)

  const { data: projects, isLoading } = useQuery<Project[]>({ queryKey: ['projects'], queryFn: () => api.get('/projects') })

  const createMut = useMutation({
    mutationFn: (data: { name: string; prompt: string }) => api.post('/projects', data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setName(''); setPrompt(''); navigate(`/projects/${result.id}`)
    },
    onError: (caught: any) => setError(caught?.message || 'Impossibile creare il progetto. Verifica che il servizio sia attivo.'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })

  const handleCreate = (event: React.FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    setError('')
    createMut.mutate({ name: name.trim(), prompt: prompt.trim() })
  }

  const handleWizardCreate = (wName: string, wPrompt: string, mode: 'quick' | 'wizard') => {
    createMut.mutate({ name: wName, prompt: wPrompt })
  }

  const handleDelete = (event: React.MouseEvent, project: Project) => {
    event.preventDefault(); event.stopPropagation()
    if (window.confirm(`Eliminare definitivamente “${project.name}”?`)) deleteMut.mutate(project.id)
  }

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-8 grid items-center gap-6 lg:grid-cols-[1.3fr_.7fr]">
        <div>
          <span className="inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-blue-700 dark:bg-blue-950 dark:text-blue-300">Assistente per database</span>
          <h1 className="mt-4 max-w-3xl text-3xl font-black tracking-tight text-slate-950 sm:text-4xl dark:text-white">Crea un database senza partire dal codice.</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600 dark:text-slate-300">Descrivi ciò che ti serve, aggiungi i tuoi documenti e lasciati guidare nella creazione di tabelle, relazioni e dati.</p>
        </div>
        <div className="surface grid grid-cols-3 gap-2 p-4 text-center">
          {[['1', 'Descrivi'], ['2', 'Carica'], ['3', 'Verifica']].map(([step, label]) => (
            <div key={step} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
              <span className="mx-auto grid h-7 w-7 place-items-center rounded-full bg-blue-600 text-xs font-bold text-white">{step}</span>
              <span className="mt-2 block text-xs font-semibold">{label}</span>
            </div>
          ))}
        </div>
      </header>

      <section className="surface mb-10 overflow-hidden" aria-labelledby="new-project-title">
        <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-blue-50 to-indigo-50 px-5 py-4 sm:px-7 dark:border-slate-800 dark:from-blue-950/40 dark:to-indigo-950/40">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">Inizia qui</p>
            <h2 id="new-project-title" className="mt-1 text-xl font-bold">Crea un nuovo progetto</h2>
          </div>
          <button
            onClick={() => setIsWizardOpen(true)}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-xs font-bold text-white shadow hover:from-blue-700 hover:to-indigo-700"
          >
            🧙‍♂️ Apri Wizard Guidato
          </button>
        </div>
        <form onSubmit={handleCreate} className="space-y-5 p-5 sm:p-7">
          <div>
            <label htmlFor="project-name" className="mb-2 block text-sm font-semibold">Nome del progetto <span className="text-red-500" aria-hidden="true">*</span></label>
            <input id="project-name" type="text" placeholder="Es. Gestione biblioteca" value={name} onChange={(event) => setName(event.target.value)} className="field" required autoComplete="off" />
            <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">Scegli un nome semplice per riconoscerlo in seguito.</p>
          </div>
          <div>
            <div className="mb-2 flex items-baseline justify-between gap-3">
              <label htmlFor="project-description" className="block text-sm font-semibold">Cosa deve gestire il database?</label>
              <span className="text-xs text-slate-400">Puoi completarlo più tardi</span>
            </div>
            <textarea id="project-description" placeholder="Es. Una biblioteca con libri, autori, prestiti e lettori. Ogni libro può avere più autori..." value={prompt} onChange={(event) => setPrompt(event.target.value)} className="field min-h-28 resize-y" />
            <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">Più dettagli fornisci, più accurato sarà il primo schema proposto.</p>
          </div>
          {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
          <button type="submit" disabled={!name.trim() || createMut.isPending} className="primary-button w-full sm:w-auto">
            {createMut.isPending ? 'Creazione in corso…' : 'Crea progetto e continua →'}
          </button>
        </form>
      </section>

      <ProjectWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onCreateProject={handleWizardCreate}
      />


      <section aria-labelledby="projects-title">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Il tuo spazio di lavoro</p>
            <h2 id="projects-title" className="mt-1 text-2xl font-bold">Progetti recenti</h2>
          </div>
          {!!projects?.length && <span className="text-sm text-slate-500">{projects.length} {projects.length === 1 ? 'progetto' : 'progetti'}</span>}
        </div>

        {isLoading ? (
          <div className="surface p-8 text-center text-slate-500" role="status">Caricamento dei progetti…</div>
        ) : projects?.length === 0 ? (
          <div className="surface border-dashed p-10 text-center">
            <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-slate-800">＋</div>
            <h3 className="font-bold">Non ci sono ancora progetti</h3>
            <p className="mt-1 text-sm text-slate-500">Compila il modulo qui sopra per creare il primo.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {projects?.map((project) => (
              <article key={project.id} className="surface group relative transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:hover:border-blue-700">
                <Link to={`/projects/${project.id}`} className="block min-h-36 p-5 pr-14">
                  <span className="mb-3 grid h-10 w-10 place-items-center rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300" aria-hidden="true">▦</span>
                  <h3 className="truncate text-lg font-bold group-hover:text-blue-700 dark:group-hover:text-blue-300">{project.name}</h3>
                  <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{project.prompt || 'Nessuna descrizione: apri il progetto per iniziare.'}</p>
                  <span className="mt-4 inline-block text-sm font-semibold text-blue-600 dark:text-blue-400">Apri progetto →</span>
                </Link>
                <button onClick={(event) => handleDelete(event, project)} disabled={deleteMut.isPending} className="absolute right-4 top-4 rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30" aria-label={`Elimina ${project.name}`} title="Elimina progetto">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></svg>
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
