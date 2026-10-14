import React, { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

const numOr = (v: any, d: number) => {
  if (v === '' || v === null || v === undefined) return d
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [settingsData, setSettingsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [saveError, setSaveError] = useState('')

  const [testPrompt, setTestPrompt] = useState('Rispondi in italiano: Che giorno è oggi?')
  const [testRunning, setTestRunning] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)

  useEffect(() => {
    const load = async () => {
      try {
        setSettingsData(await api.get('/settings'))
      } catch (e) {
        console.error('Error loading settings:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSuccessMsg('')
    setSaveError('')
    try {
      const updated = await api.put('/settings', {
        vertex_model: settingsData.vertex_model,
        vertex_max_output_tokens: numOr(settingsData.vertex_max_output_tokens, 2048),
      })
      setSettingsData(updated)
      queryClient.invalidateQueries({ queryKey: ['llm-info'] })
      setSuccessMsg('Impostazioni salvate.')
      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (e: any) {
      setSaveError(`Non sono riuscito a salvare: ${e.message || e}`)
    } finally {
      setSaving(false)
    }
  }

  const runTest = async () => {
    setTestRunning(true)
    setTestResult(null)
    try {
      setTestResult(await api.post('/settings/test', { prompt: testPrompt }))
    } catch (e: any) {
      setTestResult({ success: false, error: e.message || 'Errore di connessione' })
    } finally {
      setTestRunning(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  if (!settingsData) {
    return (
      <div role="alert" className="mx-auto max-w-3xl rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
        Non riesco a leggere le impostazioni.
      </div>
    )
  }

  const models: string[] = settingsData.vertex_models || []
  const set = (patch: Record<string, any>) => setSettingsData({ ...settingsData, ...patch })

  return (
    <div className="mx-auto max-w-3xl space-y-6 py-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-tecnia-ink dark:text-white">Modello IA</h1>
        <p className="mt-1.5 text-sm text-tecnia-muted">
          Le risposte sono generate con Google Vertex AI. Puoi scegliere il modello tra quelli disponibili su Vertex.
        </p>
      </div>

      {successMsg && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300">
          {successMsg}
        </div>
      )}
      {saveError && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300">{saveError}</div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        <div className="glass p-6">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Vertex AI</h2>
          <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">Progetto Google Cloud</dt>
              <dd className="mt-1 font-mono text-slate-800 dark:text-slate-200">{settingsData.vertex_project || 'Non impostato'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">Regione</dt>
              <dd className="mt-1 font-mono text-slate-800 dark:text-slate-200">{settingsData.vertex_location}</dd>
            </div>
          </dl>

          <div className="mt-5">
            <label htmlFor="vertex-model" className="block text-xs font-semibold uppercase tracking-wider text-slate-500">Modello</label>
            <select
              id="vertex-model"
              value={settingsData.vertex_model}
              onChange={(e) => set({ vertex_model: e.target.value })}
              className="mt-1 field"
            >
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-slate-500">Progetto e regione si impostano nella configurazione del servizio.</p>
          </div>
        </div>

        <div className="glass p-6">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Lunghezza delle risposte</h2>
          <label htmlFor="llm-max-tokens" className="mt-4 block text-xs font-semibold text-slate-500">Lunghezza massima della risposta (token)</label>
          <input
            id="llm-max-tokens"
            type="number" min={256} max={65536} step={256}
            value={settingsData.vertex_max_output_tokens}
            onChange={(e) => set({ vertex_max_output_tokens: e.target.value })}
            className="mt-1 field sm:max-w-xs"
          />
          <p className="mt-1.5 text-xs text-slate-500">Più token permettono schemi e testi più lunghi, ma costano di più.</p>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-3 text-sm font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Salvataggio…' : 'Salva le impostazioni'}
        </button>
      </form>

      <div className="glass p-6">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Prova la connessione</h2>
        <p className="mt-1 text-xs text-slate-500">
          Manda un messaggio di prova a Vertex AI con il modello salvato ({settingsData.model}).
        </p>
        <label htmlFor="test-prompt" className="mt-4 block text-xs font-semibold text-slate-500">Messaggio di prova</label>
        <textarea
          id="test-prompt"
          value={testPrompt}
          onChange={(e) => setTestPrompt(e.target.value)}
          rows={2}
          className="mt-1 field"
        />
        <button
          type="button"
          onClick={runTest}
          disabled={testRunning || !testPrompt.trim()}
          className="mt-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-sm font-bold text-white shadow-md hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50"
        >
          {testRunning ? 'Invio in corso…' : 'Invia il messaggio di prova'}
        </button>

        {testResult && !testRunning && (
          <div className={`mt-4 rounded-xl border p-4 ${
            testResult.success
              ? 'border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-950/50'
              : 'border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/50'
          }`}>
            {testResult.success ? (
              <>
                <div className="text-xs font-bold text-green-700 dark:text-green-300">
                  Risposta ricevuta da {testResult.model} in {testResult.total_duration_ms} ms
                </div>
                <div className="mt-3 max-h-48 overflow-y-auto rounded-lg border border-green-100 bg-white p-3 text-sm text-slate-800 dark:border-green-900 dark:bg-slate-950 dark:text-slate-200">
                  {testResult.response}
                </div>
              </>
            ) : (
              <div className="text-xs font-semibold text-red-700 dark:text-red-300">Prova non riuscita: {testResult.error}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
