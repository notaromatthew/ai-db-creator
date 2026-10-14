import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { useAuth } from '@/context/KeycloakContext'

export interface ExampleSummary {
  name: string
  title: string
  subtitle: string
  icon: string
  tables: number
  relationships: number
}

/** Elenco pubblico degli esempi già analizzati: si legge senza login. */
export default function ExamplesPage() {
  const { authenticated, register } = useAuth()
  const { data, isLoading, isError } = useQuery<{ examples: ExampleSummary[] }>({
    queryKey: ['examples'],
    queryFn: () => api.get('/examples'),
  })

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Esempi già analizzati</h1>
        <p className="mt-1.5 text-tecnia-muted dark:text-slate-400">
          Tre casi reali, dal documento allo schema. Si leggono senza registrarsi.
        </p>
      </header>

      {isLoading && <div className="glass p-8 text-center text-tecnia-muted" role="status">Carico gli esempi…</div>}
      {isError && <div className="glass p-8 text-center text-tecnia-muted" role="alert">Non riesco a caricare gli esempi. Riprova fra qualche istante.</div>}

      {data && (
        <ul className="grid gap-5 md:grid-cols-3">
          {data.examples.map((ex) => (
            <li key={ex.name} className="glass flex flex-col p-5">
              <span className="material-symbols-outlined !text-[28px] text-tecnia-primary" aria-hidden="true">{ex.icon}</span>
              <h2 className="mt-2 text-lg font-bold">{ex.title.split(':')[0]}</h2>
              <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">{ex.subtitle}</p>
              <p className="mt-3 flex flex-wrap gap-2">
                <span className="tag">{ex.tables} tabelle</span>
                <span className="tag">{ex.relationships} relazioni</span>
              </p>
              <Link to={`/app/examples/${ex.name}`} className="secondary-button mt-5 self-start">Apri l'esempio</Link>
            </li>
          ))}
        </ul>
      )}

      {!authenticated && (
        <div className="glass flex flex-wrap items-center justify-between gap-3 p-5">
          <span className="text-sm font-semibold">Vuoi provarlo con i tuoi documenti?</span>
          <button onClick={register} className="primary-button">Crea un account</button>
        </div>
      )}
    </div>
  )
}
