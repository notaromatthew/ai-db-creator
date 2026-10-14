import { useState, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { NormalizedSchema } from '@/types'
import Markdown from './Markdown'

interface Props {
  projectId: string
  schema: NormalizedSchema | null
  documentIds: string[]
  /** Schema reso definitivo: la conversazione resta leggibile ma non si scrive piu'. */
  locked?: boolean
  /** Ruolo di sola lettura. */
  readOnly?: boolean
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  /** Proposta di modifica in attesa di conferma (solo l'ultima risposta puo' esserlo). */
  proposal?: boolean
}

function stripCodeBlocks(text: string): string {
  return text.replace(/```[\s\S]*?```/g, '').trim()
}

const INTRO_NEW = 'Ciao! Descrivi cosa vuoi cambiare nello schema (per esempio "aggiungi la data di consegna agli ordini"): ti propongo le modifiche e le applico quando confermi.'

export default function SchemaChat({ projectId, schema, documentIds, locked = false, readOnly = false }: Props) {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)

  const { data: history, isError: historyFailed } = useQuery<{ messages: { role: string; content: string; proposal?: boolean }[] }>({
    queryKey: ['chat-history', projectId],
    queryFn: () => api.get(`/projects/${projectId}/chat/history`),
    staleTime: Infinity,
    retry: false,
  })

  useEffect(() => {
    if (initialized.current || (!history && !historyFailed)) return
    initialized.current = true
    const saved: Message[] = (history?.messages || [])
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role as Message['role'], content: m.role === 'assistant' ? stripCodeBlocks(m.content) : m.content, proposal: !!m.proposal }))
      .filter((m) => m.content)
    setMessages(saved.length ? saved : [{ role: 'assistant', content: INTRO_NEW }])
  }, [history, historyFailed])

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages, loading])

  const disabled = locked || readOnly

  const applySchema = async (proposal: NormalizedSchema) => {
    await api.put(`/projects/${projectId}/schema`, proposal)
    queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['stats', projectId] })
    queryClient.invalidateQueries({ queryKey: ['interactions', projectId] })
  }

  const say = (content: string) => setMessages((prev) => [...prev, { role: 'assistant', content }])
  const clearProposal = () => setMessages((prev) => prev.map((m) => (m.proposal ? { ...m, proposal: false } : m)))

  const applyAndReport = async (proposal: NormalizedSchema) => {
    try {
      await applySchema(proposal)
      say('Ho aggiornato lo schema: controlla il diagramma. Il database vuoto è stato rigenerato.')
    } catch (e: any) {
      say(`Non sono riuscito ad applicare la modifica: ${e?.message || 'errore sconosciuto'}`)
    }
  }

  const sendMessage = async () => {
    const msg = input.trim()
    if (!msg || loading || disabled) return
    setInput('')
    clearProposal()
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const res = await api.post(`/projects/${projectId}/chat`, { message: msg, document_ids: documentIds })
      setMessages((prev) => [...prev, { role: 'assistant', content: stripCodeBlocks(res.response) || 'Ho capito.', proposal: !!res.proposal }])
      if (res.schema) await applyAndReport(res.schema)
    } catch (e: any) {
      say(`Qualcosa non ha funzionato: ${e?.message || 'riprova tra poco'}`)
    } finally {
      setLoading(false)
    }
  }

  const acceptProposal = async () => {
    if (loading || disabled) return
    clearProposal()
    setLoading(true)
    try {
      const res = await api.post(`/projects/${projectId}/chat/apply`, {})
      await applyAndReport(res.schema)
    } catch (e: any) {
      say(`Non sono riuscito ad applicare la modifica: ${e?.message || 'riprova tra poco'}`)
    } finally {
      setLoading(false)
    }
  }

  const dismissProposal = async () => {
    clearProposal()
    try {
      await api.post(`/projects/${projectId}/chat/dismiss`, {})
    } catch {
      /* la proposta resta scartata nella conversazione anche se il server non risponde */
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <section className="glass flex h-[520px] flex-col overflow-hidden" aria-labelledby="chat-title">
      <div className="border-b border-tecnia-line/60 p-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-fuchsia-700" aria-hidden="true">chat</span>
          <h3 id="chat-title" className="font-bold">Chiedi all'IA di modificare</h3>
        </div>
        <p className="mt-1 text-xs leading-5 text-tecnia-muted dark:text-slate-400">
          {locked
            ? 'Lo schema è definitivo: la conversazione resta qui da rileggere, ma non si può più modificare.'
            : 'Scrivi cosa cambiare: ti propongo le modifiche e lo schema si aggiorna solo quando confermi. La conversazione resta salvata nel progetto.'}
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-2xl px-3 py-2 text-sm ${m.role === 'user' ? 'whitespace-pre-wrap bg-orange-600 text-white' : 'bg-slate-100 text-tecnia-ink dark:bg-slate-800 dark:text-slate-100'}`}>
              {m.role === 'user' ? m.content : <Markdown text={m.content} />}
              {m.proposal && !disabled && i === messages.length - 1 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={acceptProposal} disabled={loading} className="primary-button !min-h-9 !px-4">Applica le modifiche</button>
                  <button type="button" onClick={dismissProposal} disabled={loading} className="secondary-button !min-h-9 !px-4">Non ora</button>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-slate-100 px-3 py-2 text-sm italic text-slate-500 dark:bg-slate-800">Sto pensando…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {disabled ? (
        <p className="flex items-center gap-2 border-t border-tecnia-line/60 p-3 text-xs font-semibold text-tecnia-muted dark:border-slate-700 dark:text-slate-400">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{locked ? 'lock' : 'visibility'}</span>
          {locked ? 'Schema definitivo: la chat è chiusa.' : 'Hai accesso in sola lettura.'}
        </p>
      ) : (
        <div className="flex gap-2 border-t border-tecnia-line/60 p-3 dark:border-slate-700">
          <input
            aria-label="Messaggio all'IA"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={loading ? 'Attendi la risposta…' : 'Es. unisci clienti e fornitori'}
            disabled={loading}
            className="field flex-1 text-sm"
          />
          <button type="button" onClick={sendMessage} disabled={loading || !input.trim()} className="secondary-button px-4" aria-label="Invia">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">send</span>
          </button>
        </div>
      )}
    </section>
  )
}
