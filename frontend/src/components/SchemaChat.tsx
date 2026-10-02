import { useState, useRef, useEffect } from 'react'
import { api } from '@/api/client'
import { useQueryClient } from '@tanstack/react-query'
import { NormalizedSchema } from '@/types'
import { emitRq4 } from '@/services/rq4Emitter'
import MarkdownMessage from './MarkdownMessage'

interface Props {
  projectId: string
  schema: NormalizedSchema | null
  documentIds: string[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function cleanDisplayResponse(text: string): string {
  // Strip only the raw JSON schema payload intended for the system, preserving all other text and code blocks
  const cleaned = text.replace(/```json\s*\{[\s\S]*?"tables"[\s\S]*?\}\s*```/gi, '').trim()
  return cleaned || text.replace(/```json[\s\S]*?```/g, '').trim() || 'Ho analizzato la richiesta e ho preparato una proposta di schema:'
}

export default function SchemaChat({ projectId, schema, documentIds }: Props) {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingSchema, setPendingSchema] = useState<NormalizedSchema | null>(null)
  const [accepting, setAccepting] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!messages.length) {
      const intro = schema
        ? 'Hai già uno schema. Puoi chiedermi di modificarlo — aggiungere tabelle, colonne o cambiare relazioni.'
        : 'Ciao! Ti aiuto a progettare un database. Descrivi quali dati devi memorizzare e ti proporrò una struttura su misura. Di cosa hai bisogno?'
      setMessages([{ role: 'assistant', content: intro }])
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const res = await api.post(`/projects/${projectId}/chat`, {
        message: msg,
        document_ids: documentIds,
      })
      const displayContent = cleanDisplayResponse(res.response)
      setMessages(prev => [...prev, { role: 'assistant', content: displayContent }])
      if (res.schema) {
        if (pendingSchema) emitRq4(projectId,{type:'ignore_suggestion',target_type:'suggestion',target_name:'schema-proposal',action:'ignore',phase:'schema',outcome:'ignored',operation_id:'chat-suggestion'}).catch(()=>{})
        setPendingSchema(res.schema)
      }
    } catch (e: any) {
      emitRq4(projectId,{type:'validation_error',target_type:'suggestion',target_name:'chat',phase:'schema',outcome:'failure',error_code:'CHAT_ERROR',operation_id:'chat-suggestion'}).catch(()=>{})
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e?.message || 'Chat failed'}` }])
    } finally {
      setLoading(false)
    }
  }

  const acceptSchema = async () => {
    if (!pendingSchema) return
    setAccepting(true)
    try {
      await api.post(`/projects/${projectId}/chat-accept`, pendingSchema)
      await emitRq4(projectId,{type:'accept_suggestion',target_type:'suggestion',target_name:'schema-proposal',action:'accept',phase:'schema',outcome:'success',operation_id:'chat-suggestion'})
      setPendingSchema(null)
      setMessages([{ role: 'assistant', content: 'Schema accettato e salvato! Ora puoi visualizzarlo e popolare le tabelle qui sotto.' }])
      queryClient.invalidateQueries({ queryKey: ['schema', projectId] })
      queryClient.invalidateQueries({ queryKey: ['interactions', projectId] })
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error saving schema: ${e?.message || 'Failed'}` }])
    } finally {
      setAccepting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="border rounded-xl dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950 flex flex-col h-[520px] shadow-sm">
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs shadow-sm ${
                m.role === 'user'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-none'
                  : 'bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none'
              }`}
            >
              {m.role === 'user' ? (
                <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
              ) : (
                <MarkdownMessage content={m.content} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl rounded-tl-none px-4 py-2.5 text-xs text-slate-500 italic flex items-center gap-2 shadow-sm">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-ping"></span>
              Sto analizzando e formulando la risposta...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {pendingSchema && (
        <div className="border-t border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/90 dark:bg-emerald-950/50 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-inner">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500"></span>
              <p className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                Proposta schema pronta: {pendingSchema.tables?.length || 0} tabelle, {pendingSchema.relationships?.length || 0} relazioni
              </p>
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {pendingSchema.tables?.map((t, idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-emerald-100/80 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                >
                  {t.name}
                </span>
              ))}
            </div>
          </div>
          <button
            onClick={acceptSchema}
            disabled={accepting}
            className="flex-shrink-0 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 transition"
          >
            {accepting ? 'Salvataggio…' : 'Accetta Schema'}
          </button>
        </div>
      )}

      {/* Quick Action Chips */}
      <div className="flex items-center gap-1.5 px-3 pt-2 text-[11px] overflow-x-auto">
        <span className="text-slate-400 font-medium whitespace-nowrap">Suggerimenti:</span>
        <button
          onClick={() => {
            setInput('Genera lo schema completo in formato JSON con tutte le tabelle, colonne e relazioni.')
          }}
          disabled={loading}
          className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2 py-1 text-slate-600 dark:text-slate-300 hover:border-blue-500 hover:text-blue-600 whitespace-nowrap transition"
        >
          📐 Genera lo schema adesso
        </button>
        <button
          onClick={() => {
            setInput('Verifica che tutte le tabelle rispettino la Terza Forma Normale (3NF) e aggiungi eventuali chiavi esterne mancanti.')
          }}
          disabled={loading}
          className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-2 py-1 text-slate-600 dark:text-slate-300 hover:border-blue-500 hover:text-blue-600 whitespace-nowrap transition"
        >
          🔄 Normalizza in 3NF
        </button>
      </div>

      <div className="border-t border-slate-200 dark:border-slate-800 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={loading ? 'Elaborazione in corso...' : 'Scrivi un messaggio...'}
          disabled={loading}
          className="flex-1 border rounded-xl px-3.5 py-2 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 dark:text-white disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold px-4 py-2 rounded-xl text-xs shadow-sm disabled:opacity-50 transition"
        >
          Invia
        </button>
      </div>
    </div>
  )
}
