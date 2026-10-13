import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useAuth } from '@/context/KeycloakContext'
import CompareTab from './CompareTab'
import DiagnosisTab from './DiagnosisTab'
import LaunchTab from './LaunchTab'
import RunsTab from './RunsTab'
import StudyAdminTab from './StudyAdminTab'
import type { Meta } from './types'

const TABS = [
  { id: 'run', label: 'Run', icon: 'table_rows' },
  { id: 'confronti', label: 'Confronti', icon: 'bar_chart' },
  { id: 'lancio', label: 'Lancio e coda', icon: 'play_circle' },
  { id: 'diagnosi', label: 'Diagnosi', icon: 'troubleshoot' },
  { id: 'studio', label: 'Studio', icon: 'groups' },
] as const
type TabId = (typeof TABS)[number]['id']

export const canResearch = (roles: string[], isAdmin: boolean) => isAdmin || roles.includes('aidb-researcher')

export default function ResearchPage() {
  const { roles, isAdmin } = useAuth()
  const [tab, setTab] = useState<TabId>('run')
  const [meta, setMeta] = useState<Meta | null>(null)
  const [error, setError] = useState('')
  const allowed = canResearch(roles ?? [], !!isAdmin)

  const loadMeta = useCallback(() => {
    api.get('/research/meta').then(setMeta).catch((e) => setError((e as Error).message))
  }, [])
  useEffect(() => { if (allowed) loadMeta() }, [allowed, loadMeta])

  if (!allowed) {
    return (
      <div className="glass mx-auto my-10 max-w-md p-8 text-center" role="alert">
        <h1 className="text-xl font-bold">Area riservata alla ricerca</h1>
        <p className="mt-2 text-sm text-tecnia-muted">Questa sezione è solo per chi conduce lo studio. Se ti serve, chiedi l'accesso a un amministratore.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <span className="tag text-tecnia-magentaDeep dark:text-pink-300">Modalità ricerca</span>
        <h1 className="mt-2.5 text-3xl font-bold tracking-tight">Ricerca</h1>
        <p className="mt-1.5 max-w-2xl text-base text-tecnia-muted dark:text-slate-300">Run di benchmark, confronti con intervalli di confidenza, lancio con stima del costo e controllo dello studio con i partecipanti.</p>
        {meta && <p className="mt-1 text-xs text-tecnia-muted">Versione del software: <code>{meta.software_revision}</code></p>}
      </div>
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      <div role="tablist" aria-label="Sezioni della ricerca" className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <button key={t.id} role="tab" type="button" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls={`panel-${t.id}`}
            onClick={() => setTab(t.id)}
            className={`rounded-full px-4 py-2 font-headline text-sm font-semibold transition ${tab === t.id ? 'bg-orange-50 text-tecnia-primary dark:bg-slate-800' : 'text-tecnia-muted hover:bg-white/70 dark:hover:bg-slate-800'}`}>
            <span aria-hidden="true" className="material-symbols-outlined mr-1 align-middle !text-[18px]">{t.icon}</span>{t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === 'run' && <RunsTab meta={meta} />}
        {tab === 'confronti' && <CompareTab meta={meta} />}
        {tab === 'lancio' && <LaunchTab meta={meta} onLaunched={loadMeta} />}
        {tab === 'diagnosi' && <DiagnosisTab meta={meta} />}
        {tab === 'studio' && <StudyAdminTab />}
      </div>
    </div>
  )
}
