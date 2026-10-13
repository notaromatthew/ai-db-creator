import { useState, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { NormalizedSchema } from '@/types'

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
}

function stripCodeBlocks(text: string): string {
  return text.replace(/```[\s\S]*?```/g, '').trim()
}

const INTRO_NEW = 'Ciao! Descrivi cosa vuoi cambiare nello schema (per esempio "aggiungi la data di consegna agli ordini") e lo aggiorno io.'

export default function SchemaChat({ projectId, schema, documentIds, locked = false, readOnly = false }: Props) {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)

  const { data: history, isError: historyFailed } = useQuery<{ messages: { role: string; content: string }[] }>({
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
      .map((m) => ({ role: m.role as Message['role'], content: m.role === 'assistant' ? stripCodeBlocks(m.content) : m.content }))
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

  const sendMessage = async () => {
    const msg = input.trim()
    if (!msg || loading || disabled) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const res = await api.post(`/projects/${projectId}/chat`, { message: msg, document_ids: documentIds })
      const text = stripCodeBlocks(res.response) || 'Ho preparato una modifica allo schema.'
      setMessages((prev) => [...prev, { role: 'assistant', content: text }])
      if (res.schema) {
        try {
          await applySchema(res.schema)
          setMessages((prev) => [...prev, { role: 'assistant', content: 'Ho aggiornato lo schema: controlla il diagramma. Il database vuoto è stato rigenerato.' }])
        } catch (e: any) {
          setMessages((prev) => [...prev, { role: 'assistant', content: `Non sono riuscito ad applicare la modifica: ${e?.message || 'errore sconosciuto'}` }])
        }
      }
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Qualcosa non ha funzionato: ${e?.message || 'riprova tra poco'}` }])
    } finally {
      setLoading(false)
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
            : 'Scrivi cosa cambiare: lo schema si aggiorna e approvi tu con "Continua". La conversazione resta salvata nel progetto.'}
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${m.role === 'user' ? 'bg-orange-600 text-white' : 'bg-slate-100 text-tecnia-ink dark:bg-slate-800 dark:text-slate-100'}`}>
              {m.content}
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
