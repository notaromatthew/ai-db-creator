import { Suspense, lazy, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { useAuth } from '@/context/KeycloakContext'
import { NormalizedSchema } from '@/types'
import type { ExampleSummary } from './ExamplesPage'

const SchemaDiagram = lazy(() => import('@/components/SchemaDiagram'))

interface ExampleDetail extends ExampleSummary {
  intro: string[]
  choices: string[]
  notes: string[]
  prompt: string
  schema: NormalizedSchema
  sources: { name: string; size: number; kind: string }[]
  data: { table: string; columns: string[]; rows: (string | number | null)[][]; total: number }[]
}

const sizeLabel = (n: number) => (n < 1024 ? `${n} B` : `${Math.round(n / 1024)} KB`)
const cell = (v: string | number | null) => (v === null ? '' : String(v))

/** Dettaglio pubblico di un esempio: documenti, richiesta, schema e dati, tutto in sola lettura. */
export default function ExampleDetailPage() {
  const { name = '' } = useParams()
  const { authenticated, register } = useAuth()
  const [tab, setTab] = useState(0)
  const { data, isLoading, isError } = useQuery<ExampleDetail>({
    queryKey: ['example', name],
    queryFn: () => api.get(`/examples/${encodeURIComponent(name)}`),
  })

  if (isLoading) return <div className="glass mx-auto mt-10 max-w-md p-8 text-center text-tecnia-muted" role="status">Apro l'esempio…</div>

  if (isError || !data) {
    return (
      <div className="glass mx-auto mt-10 max-w-md p-8 text-center" role="alert">
        <h1 className="text-xl font-bold">Questo esempio non esiste</h1>
        <Link to="/app/examples" className="primary-button mt-5">Torna agli esempi</Link>
      </div>
    )
  }

  const current = data.data[Math.min(tab, data.data.length - 1)]
  const base = `/api/examples/${encodeURIComponent(data.name)}/files`

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8">
      <header>
        <nav aria-label="Percorso" className="text-sm text-tecnia-muted">
          <Link to="/app/examples" className="hover:underline">Esempi</Link> / {data.title.split(':')[0]}
        </nav>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">{data.title}</h1>
        <div className="mt-3 space-y-2 text-tecnia-muted dark:text-slate-400">
          {data.intro.map((p) => <p key={p}>{p}</p>)}
        </div>
      </header>

      <section aria-labelledby="ex-sources" className="flex flex-col gap-3">
        <h2 id="ex-sources" className="text-xl font-bold">1. Documenti di partenza</h2>
        <ul className="flex flex-wrap gap-2">
          {data.sources.map((f) => (
            <li key={f.name}>
              <a className="tag hover:underline" href={`${base}/${encodeURIComponent(f.name)}`} download>
                {f.name} · {sizeLabel(f.size)}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="ex-prompt" className="flex flex-col gap-3">
        <h2 id="ex-prompt" className="text-xl font-bold">2. La richiesta</h2>
        <pre className="glass whitespace-pre-wrap p-4 font-mono text-xs">{data.prompt}</pre>
      </section>

      <section aria-labelledby="ex-schema" className="flex flex-col gap-3">
        <h2 id="ex-schema" className="text-xl font-bold">3. Lo schema</h2>
        {data.choices.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-tecnia-muted dark:text-slate-400">
            {data.choices.map((c) => <li key={c}>{c}</li>)}
          </ul>
        )}
        <Suspense fallback={<div className="glass p-8 text-center text-tecnia-muted" role="status">Disegno il diagramma…</div>}>
          <SchemaDiagram schema={{ ...data.schema, relationships: data.schema.relationships ?? [] }} />
        </Suspense>
        <div className="grid gap-5 md:grid-cols-2">
          {data.schema.tables.map((t) => (
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

      {current && (
        <section aria-labelledby="ex-data" className="flex flex-col gap-3">
          <h2 id="ex-data" className="text-xl font-bold">4. I dati</h2>
          <div role="tablist" aria-label="Tabelle" className="flex flex-wrap gap-2">
            {data.data.map((d, i) => (
              <button key={d.table} role="tab" aria-selected={i === tab} onClick={() => setTab(i)}
                className={i === tab ? 'primary-button !min-h-9 !px-4' : 'secondary-button !min-h-9 !px-4'}>{d.table}</button>
            ))}
          </div>
          <div className="glass overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead><tr className="bg-slate-100 text-left text-xs dark:bg-slate-800">{current.columns.map((c) => <th key={c} className="px-3 py-2 font-semibold">{c}</th>)}</tr></thead>
              <tbody>
                {current.rows.map((r, i) => (
                  <tr key={i} className="border-t border-tecnia-line/40">{r.map((v, j) => <td key={j} className="px-3 py-1.5">{cell(v)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-tecnia-muted">
            {current.total > current.rows.length ? `Prime ${current.rows.length} righe su ${current.total}.` : `${current.total} righe.`} Sola lettura.
          </p>
        </section>
      )}

      {data.notes.length > 0 && (
        <section aria-labelledby="ex-notes" className="flex flex-col gap-2">
          <h2 id="ex-notes" className="text-xl font-bold">Da sapere</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-tecnia-muted dark:text-slate-400">{data.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </section>
      )}

      <section aria-labelledby="ex-try" className="glass flex flex-wrap items-center justify-between gap-3 p-5">
        <h2 id="ex-try" className="text-base font-bold">Prova con i tuoi documenti</h2>
        {authenticated
          ? <Link to="/app" className="primary-button">Vai ai tuoi progetti</Link>
          : <button onClick={register} className="primary-button">Crea un account</button>}
      </section>
    </div>
  )
}
