import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { configureRq4Scope, emitRq4 } from '../services/rq4Emitter'

type ExperimentSession = { session_id:string; project_id:string; status: string; condition: string; deadline_at: string; capabilities: string[] }
const ExperimentContext = createContext<{session: ExperimentSession | null; can: (capability: string) => boolean}>({session: null, can: () => true})
export const useExperiment = () => useContext(ExperimentContext)

export default function ExperimentShell({ projectId, children }: {projectId: string; children: React.ReactNode}) {
  const [session, setSession] = useState<ExperimentSession | null>(null)
  const [seconds, setSeconds] = useState<number | null>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    api.get('/experiments/sessions/current')
      .catch(() => api.post('/experiments/sessions', {project_id: projectId, protocol_version: 'pilot-draft-v1', duration_minutes: 45}))
      .then(async value => { if (active && value?.project_id === projectId) { const state=await api.get(`/projects/${projectId}/interactions-next-sequence`); configureRq4Scope(projectId,value.session_id,state.next_sequence); setSession(value) } })
      .catch(() => {})
    return () => { active = false }
  }, [projectId])

  useEffect(() => {
    if (!session) return
    const update = () => setSeconds(Math.max(0, Math.floor((Date.parse(session.deadline_at) - Date.now()) / 1000)))
    update(); const timer = window.setInterval(update, 1000)
    return () => window.clearInterval(timer)
  }, [session])

  useEffect(() => {
    if (!session || !session.capabilities.includes('rq4_event')) return
    const operationId = `navigation-open`
    emitRq4(projectId, {type:'navigation',target_type:'project',target_name:'workspace',action:'open',phase:'schema',operation_id:operationId}).catch(() => {})
  }, [projectId, session])

  const transition = async (target: 'completed'|'withdrawn') => {
    if (!window.confirm(target === 'withdrawn' ? 'Confermi il ritiro? I dati della sessione saranno eliminati.' : 'Confermi il completamento?')) return
    try { await emitRq4(projectId,{type:target==='withdrawn'?'task_abandon':'task_complete',target_type:'project',target_name:'workspace',action:target==='withdrawn'?'close':'complete',phase:'completion',operation_id:`transition-${target}`}); setSession(await api.post(`/experiments/sessions/current/${target}`, {})) }
    catch (error: any) { setMessage(error?.status === 409 ? 'La sessione è scaduta.' : error?.message || 'Operazione non disponibile.') }
  }
  const value = useMemo(() => ({session, can: (capability: string) => !session || session.capabilities.includes(capability)}), [session])
  return <ExperimentContext.Provider value={value}>
    {session && <section className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm" aria-label="Sessione sperimentale">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span><strong>Percorso assegnato</strong> · {session.status} · {seconds == null ? '—' : `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`}</span>
        <span className="text-xs">Strumenti disponibili: {session.capabilities.join(', ')}</span>
        <span className="flex gap-2"><button onClick={() => transition('completed')} className="secondary-button">Completa</button><button onClick={() => transition('withdrawn')} className="secondary-button">Ritirati</button></span>
      </div>{message && <p role="alert">{message}</p>}
    </section>}
    {children}
  </ExperimentContext.Provider>
}
