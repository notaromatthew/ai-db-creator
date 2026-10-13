import { Suspense, lazy } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { NormalizedSchema } from '@/types'

const SchemaDiagram = lazy(() => import('@/components/SchemaDiagram'))

interface SharedProject { name: string; schema: NormalizedSchema | null; read_only: boolean }

/** Vista pubblica in sola lettura: nome e schema del progetto, senza login. */
export default function SharedProjectPage(_props: { lang?: 'it' | 'en' }) {
  const { token = '' } = useParams()
  const { data, isLoading, isError } = useQuery<SharedProject>({
    queryKey: ['shared', token],
    queryFn: () => api.get(`/shared/${encodeURIComponent(token)}`),
    retry: false,
  })

  if (isLoading) return <div className="glass mx-auto mt-10 max-w-md p-8 text-center text-tecnia-muted" role="status">Sto aprendo il progetto condiviso…</div>

  if (isError || !data) {
    return (
      <div className="glass mx-auto mt-10 max-w-md p-8 text-center" role="alert">
        <span className="material-symbols-outlined !text-[36px] text-tecnia-primary">link_off</span>
        <h1 className="mt-2 text-xl font-bold">Questo link non è valido</h1>
        <p className="mt-2 text-sm text-tecnia-muted dark:text-slate-400">Può essere scaduto o essere stato revocato da chi lo ha condiviso. Chiedi di riceverne uno nuovo.</p>
        <Link to="/app" className="primary-button mt-5">Vai ad AI-DB-Creator</Link>
      </div>
    )
  }

  const tables = data.schema?.tables ?? []
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="tag text-tecnia-magentaDeep">Sola lettura</span>
          <h1 className="mt-3 text-3xl font-bold tracking-tight">{data.name}</h1>
          <p className="mt-1.5 text-tecnia-muted dark:text-slate-400">Stai guardando lo schema di un progetto condiviso con te. Non puoi modificarlo e i documenti caricati non sono visibili.</p>
        </div>
        <Link to="/app" className="secondary-button">Crea il tuo database</Link>
      </header>

      {tables.length === 0 ? (
        <div className="glass p-8 text-center text-tecnia-muted">Il proprietario non ha ancora generato lo schema di questo progetto.</div>
      ) : (
        <>
          <section aria-labelledby="diagram-title" className="flex flex-col gap-3">
            <h2 id="diagram-title" className="text-xl font-bold">Diagramma</h2>
            <Suspense fallback={<div className="glass p-8 text-center text-tecnia-muted" role="status">Disegno il diagramma…</div>}>
              <SchemaDiagram schema={{ ...data.schema!, relationships: data.schema!.relationships ?? [] }} />
            </Suspense>
          </section>

          <section aria-labelledby="tables-title" className="flex flex-col gap-3">
            <h2 id="tables-title" className="text-xl font-bold">Tabelle</h2>
            <div className="grid gap-5 md:grid-cols-2">
              {tables.map((t) => (
                <article key={t.name} className="glass p-5">
                  <h3 className="text-lg font-bold">{t.name}</h3>
                  {t.description && <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">{t.description}</p>}
                  <table className="mt-3 w-full text-sm">
                    <thead><tr className="text-left text-xs uppercase tracking-wide text-tecnia-muted"><th className="pb-1 font-semibold">Colonna</th><th className="pb-1 font-semibold">Tipo</th><th className="pb-1 font-semibold">Note</th></tr></thead>
                    <tbody>
                      {t.columns.map((c) => (
                        <tr key={c.name} className="border-t border-tecnia-line/40">
                          <td className="py-1.5 font-semibold">{c.name}</td>
                          <td className="py-1.5 font-mono text-xs">{c.data_type}</td>
                          <td className="py-1.5 text-xs text-tecnia-muted">
                            {[c.is_primary_key && 'chiave', c.is_foreign_key && `rimanda a ${c.foreign_key_table ?? 'altra tabella'}`, c.is_unique && 'unico', c.is_not_null && 'obbligatorio'].filter(Boolean).join(' · ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
