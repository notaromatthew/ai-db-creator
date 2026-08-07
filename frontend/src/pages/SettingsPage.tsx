import React, { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [settingsData, setSettingsData] = useState<any>(null)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [loadingModels, setLoadingModels] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  useEffect(() => {
    if (settingsData && (settingsData.llm_provider === 'ollama' || settingsData.use_ollama)) {
      fetchOllamaModels(settingsData.ollama_base_url, settingsData.ollama_api_key)
    }
  }, [settingsData?.ollama_base_url, settingsData?.ollama_api_key, settingsData?.llm_provider, settingsData?.ollama_mode])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const res = await api.get('/settings')
      setSettingsData(res)
      if (res.llm_provider === 'ollama' || res.use_ollama) {
        fetchOllamaModels(res.ollama_base_url, res.ollama_api_key)
      }
    } catch (e) {
      console.error('Error loading settings:', e)
    } finally {
      setLoading(false)
    }
  }

  const fetchOllamaModels = async (baseUrl: string, apiKey: string) => {
    setLoadingModels(true)
    try {
      const query = new URLSearchParams()
      if (baseUrl) query.append('base_url', baseUrl)
      if (apiKey !== undefined && apiKey !== null) query.append('api_key', apiKey)
      const res = await api.get(`/settings/ollama-models?${query.toString()}`)
      const fetchedModels: string[] = res?.models || []
      setOllamaModels(fetchedModels)
      if (fetchedModels.length > 0) {
        setSettingsData((prev: any) => {
          if (!prev) return prev
          const currentModel = prev.ollama_model
          if (!currentModel || !fetchedModels.includes(currentModel)) {
            return { ...prev, ollama_model: fetchedModels[0] }
          }
          return prev
        })
      }
    } catch (e) {
      console.warn('Could not list Ollama models:', e)
      setOllamaModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const handleProviderChange = (provider: string) => {
    setSettingsData((prev: any) => ({
      ...prev,
      llm_provider: provider,
      use_ollama: provider === 'ollama',
    }))
  }

  const handleOllamaModeChange = (mode: 'remote' | 'local') => {
    const isRemote = mode === 'remote'
    const targetUrl = isRemote
      ? 'https://ollamaapi-u11fj34m2h9druz26hamz3xb.89.168.29.98.sslip.io'
      : 'http://localhost:11434'

    setSettingsData((prev: any) => ({
      ...prev,
      ollama_mode: mode,
      ollama_base_url: targetUrl,
      ollama_api_key: prev?.ollama_api_key || '',
    }))
  }



  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSuccessMsg('')
    try {
      const payload: any = {
        llm_provider: settingsData.llm_provider || 'ollama',
        use_ollama: (settingsData.llm_provider || 'ollama') === 'ollama',
        ollama_mode: settingsData.ollama_mode || 'remote',
        ollama_model: settingsData.ollama_model || 'gemma2:9b',
        ollama_base_url: settingsData.ollama_base_url || '',
        ollama_api_key: settingsData.ollama_api_key || '',
        google_model: settingsData.google_model || 'gemini-2.0-flash',
        google_api_key: settingsData.google_api_key || '',
        openai_model: settingsData.openai_model || 'gpt-4o-mini',
        openai_api_key: settingsData.openai_api_key || '',
        groq_model: settingsData.groq_model || 'llama3-70b-8192',
        groq_api_key: settingsData.groq_api_key || '',
        openrouter_model: settingsData.openrouter_model || 'openai/gpt-4o-mini',
        openrouter_api_key: settingsData.openrouter_api_key || '',
        llm_temperature: Number(settingsData.llm_temperature) || 0.1,
        llm_top_p: Number(settingsData.llm_top_p) || 0.95,
        llm_max_tokens: Number(settingsData.llm_max_tokens) || 4096,
        llm_max_requests_per_minute: Number(settingsData.llm_max_requests_per_minute) || 15,
      }

      const updated = await api.put('/settings', payload)
      setSettingsData(updated)
      queryClient.invalidateQueries({ queryKey: ['llm-info'] })
      setSuccessMsg('Impostazioni salvate con successo!')

      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (e: any) {
      console.error('Save settings error:', e)
      alert(`Errore durante il salvataggio: ${e.message || e}`)
    } finally {
      setSaving(false)
    }
  }


  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  const currentProvider = settingsData?.llm_provider || 'ollama'
  const isOllamaRemote = (settingsData?.ollama_mode || 'remote') === 'remote'

  return (
    <div className="mx-auto max-w-3xl space-y-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Configurazione Provider & Iperparametri AI</h1>
          <p className="text-xs text-slate-500">
            Seleziona il provider attivo. Per Ollama, i modelli disponibili vengono letti in tempo reale dal server scelto (`ollama list`).
          </p>
        </div>
      </div>

      {successMsg && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300">
          ✓ {successMsg}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Step 1: Provider Selection */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">1. Selezione Provider AI</h3>
          <div className="mt-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">Provider Principale</label>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[
                { id: 'ollama', name: 'Ollama', badge: 'Predefinito' },
                { id: 'google', name: 'Google Gemini' },
                { id: 'openai', name: 'OpenAI' },
                { id: 'groq', name: 'Groq' },
                { id: 'openrouter', name: 'OpenRouter' },
              ].map((prov) => (
                <button
                  type="button"
                  key={prov.id}
                  onClick={() => handleProviderChange(prov.id)}
                  className={`relative flex flex-col items-center justify-center rounded-xl border p-3 text-center transition-all ${
                    currentProvider === prov.id
                      ? 'border-blue-600 bg-blue-50/50 text-blue-600 ring-2 ring-blue-600/20 dark:border-blue-500 dark:bg-blue-950/30 dark:text-blue-400'
                      : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300'
                  }`}
                >
                  <span className="text-sm font-bold">{prov.name}</span>
                  {prov.badge && (
                    <span className="mt-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/60 dark:text-blue-300">
                      {prov.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Step 2: Dynamic Provider Configuration */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            2. Configurazione Specifica: <span className="text-blue-600 dark:text-blue-400 uppercase">{currentProvider}</span>
          </h3>

          {/* OLLAMA DYNAMIC FORM WITH MODEL DROPDOWN */}
          {currentProvider === 'ollama' && (
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500">Modalità Istanza Ollama</label>
                <div className="mt-2 flex gap-4">
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name="ollama_mode"
                      value="remote"
                      checked={isOllamaRemote}
                      onChange={() => handleOllamaModeChange('remote')}
                      className="h-4 w-4 text-blue-600"
                    />
                    🌐 Remoto (Server Online)
                  </label>
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                    <input
                      type="radio"
                      name="ollama_mode"
                      value="local"
                      checked={!isOllamaRemote}
                      onChange={() => handleOllamaModeChange('local')}
                      className="h-4 w-4 text-blue-600"
                    />
                    💻 Locale (Localhost)
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-500">
                    {isOllamaRemote ? 'Endpoint API Ollama Remoto' : 'Endpoint Server Locale'}
                  </label>
                  <input
                    type="text"
                    value={settingsData.ollama_base_url || ''}
                    onChange={(e) => setSettingsData({ ...settingsData, ollama_base_url: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                  />
                </div>

                {isOllamaRemote && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-500">Bearer Auth Token</label>
                    <input
                      type="password"
                      value={settingsData.ollama_api_key || ''}
                      onChange={(e) => setSettingsData({ ...settingsData, ollama_api_key: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                    />
                  </div>
                )}

                {/* DYNAMIC OLLAMA MODEL SELECT DROPDOWN */}
                <div className="sm:col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-slate-500">
                      Modelli Disponibili sul Server ({isOllamaRemote ? 'Remoto' : 'Locale'})
                    </label>
                    <button
                      type="button"
                      onClick={() => fetchOllamaModels(settingsData.ollama_base_url, settingsData.ollama_api_key)}
                      className="text-xs font-semibold text-blue-600 hover:underline dark:text-blue-400"
                    >
                      🔄 Aggiorna Lista (`ollama list`)
                    </button>
                  </div>

                  {loadingModels ? (
                    <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
                      Lettura dei modelli dal server Ollama...
                    </div>
                  ) : ollamaModels.length > 0 ? (
                    <select
                      value={settingsData.ollama_model || ollamaModels[0]}
                      onChange={(e) => setSettingsData({ ...settingsData, ollama_model: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm font-semibold font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                    >
                      {ollamaModels.map((m) => (
                        <option key={m} value={m}>
                          📦 {m}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="mt-1 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
                      ⚠️ Impossibile contattare il server Ollama o nessun modello trovato. Modello predefinito selezionato: <code className="font-bold">{settingsData.ollama_model}</code>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* GOOGLE DYNAMIC FORM */}
          {currentProvider === 'google' && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-500">Google Gemini API Key</label>
                <input
                  type="password"
                  placeholder="AIzaSy..."
                  value={settingsData.google_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, google_api_key: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500">Nome Modello Gemini</label>
                <input
                  type="text"
                  placeholder="gemini-2.0-flash"
                  value={settingsData.google_model || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, google_model: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          )}

          {/* OPENAI DYNAMIC FORM */}
          {currentProvider === 'openai' && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-500">OpenAI API Key</label>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={settingsData.openai_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openai_api_key: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500">Nome Modello OpenAI</label>
                <input
                  type="text"
                  placeholder="gpt-4o-mini"
                  value={settingsData.openai_model || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openai_model: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          )}

          {/* GROQ DYNAMIC FORM */}
          {currentProvider === 'groq' && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-500">Groq API Key</label>
                <input
                  type="password"
                  placeholder="gsk_..."
                  value={settingsData.groq_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, groq_api_key: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500">Nome Modello Groq</label>
                <input
                  type="text"
                  placeholder="llama3-70b-8192"
                  value={settingsData.groq_model || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, groq_model: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          )}

          {/* OPENROUTER DYNAMIC FORM */}
          {currentProvider === 'openrouter' && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-500">OpenRouter API Key</label>
                <input
                  type="password"
                  placeholder="sk-or-..."
                  value={settingsData.openrouter_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openrouter_api_key: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500">Nome Modello OpenRouter</label>
                <input
                  type="text"
                  placeholder="openai/gpt-4o-mini"
                  value={settingsData.openrouter_model || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openrouter_model: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>
          )}
        </div>

        {/* Step 3: Hyperparameters */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">3. Iperparametri di Generazione</h3>
          <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-500">
                <span>Temperatura</span>
                <span className="font-mono text-blue-600 dark:text-blue-400">{settingsData.llm_temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settingsData.llm_temperature}
                onChange={(e) => setSettingsData({ ...settingsData, llm_temperature: e.target.value })}
                className="mt-2 w-full accent-blue-600"
              />
              <span className="text-[10px] text-slate-400">Valori bassi (0.0-0.2) aumentano il determinismo degli schemi.</span>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-500">
                <span>Top-P</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">{settingsData.llm_top_p}</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settingsData.llm_top_p}
                onChange={(e) => setSettingsData({ ...settingsData, llm_top_p: e.target.value })}
                className="mt-2 w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500">Max Tokens per Risposta</label>
              <input
                type="number"
                value={settingsData.llm_max_tokens}
                onChange={(e) => setSettingsData({ ...settingsData, llm_max_tokens: e.target.value })}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500">Rate Limit (Richieste/Minuto)</label>
              <input
                type="number"
                value={settingsData.llm_max_requests_per_minute}
                onChange={(e) => setSettingsData({ ...settingsData, llm_max_requests_per_minute: e.target.value })}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-mono text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Salvataggio in corso...' : 'Salva Impostazioni'}
          </button>
        </div>
      </form>
    </div>
  )
}
