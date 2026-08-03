import { useState, useRef, useEffect } from 'react'
import { api } from '@/api/client'
import { useQueryClient } from '@tanstack/react-query'
import { NormalizedSchema } from '@/types'

interface Props {
  projectId: string
  schema: NormalizedSchema | null
  documentIds: string[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function stripCodeBlocks(text: string): string {
  return text.replace(/```[\s\S]*?```/g, '').trim()
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
      const displayContent = stripCodeBlocks(res.response) || '(schema proposal)'
      setMessages(prev => [...prev, { role: 'assistant', content: displayContent }])
      if (res.schema) {
        setPendingSchema(res.schema)
      }
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e?.message || 'Chat failed'}` }])
    } finally {
      setLoading(false)
    }
  }

  const acceptSchema = async () => {
    if (!pendingSchema) return
    setAccepting(true)
    try {
      await api.put(`/projects/${projectId}/schema`, pendingSchema)
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
    <div className="border rounded dark:border-gray-600 flex flex-col h-[500px]">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2 text-sm text-gray-500 italic">Sto pensando...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {pendingSchema && (
        <div className="px-4 py-2 border-t dark:border-gray-600 bg-green-50 dark:bg-green-900/20">
          <p className="text-sm font-medium text-green-800 dark:text-green-200 mb-1">Proposta schema pronta</p>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
            {pendingSchema.tables?.length || 0} tabelle, {pendingSchema.relationships?.length || 0} relazioni
          </p>
          <button
            onClick={acceptSchema}
            disabled={accepting}
            className="bg-green-600 text-white px-4 py-1 rounded text-sm disabled:opacity-50"
          >
            {accepting ? 'Salvataggio...' : 'Accetta Schema'}
          </button>
        </div>
      )}

      <div className="border-t dark:border-gray-600 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={loading ? 'Attendi risposta...' : 'Scrivi un messaggio...'}
          disabled={loading}
          className="flex-1 border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-white disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
        >
          Invia
        </button>
      </div>
    </div>
  )
}
