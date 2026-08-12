import React, { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function BenchmarkPage() {
  const [scenarios, setScenarios] = useState<any[]>([])
  const [resultsData, setResultsData] = useState<{ results: any[]; votes: any[] }>({ results: [], votes: [] })
  const [selectedScenario, setSelectedScenario] = useState('ecommerce')
  const [selectedProvider, setSelectedProvider] = useState('ollama')
  const [selectedModel, setSelectedModel] = useState('gemma2:9b')
  const [ollamaModels, setOllamaModels] = useState<string[]>(['gemma2:9b', 'qwen3:0.6b', 'llama3.2:1b', 'gemma3:270m'])
  const [temperature, setTemperature] = useState(0.1)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [runSuccess, setRunSuccess] = useState('')
  const [progressState, setProgressState] = useState<{
    status: string
    progress: number
    message: string
    etc_seconds: number | null
  }>({ status: 'idle', progress: 0, message: '', etc_seconds: null })

  // Expert Vote State
  const [schemaRating, setSchemaRating] = useState(5)
  const [dataRating, setDataRating] = useState(5)
  const [comment, setComment] = useState('')
  const [voting, setVoting] = useState(false)
  const [voteSuccess, setVoteSuccess] = useState('')

  useEffect(() => {
    loadData()
    checkRunningBenchmark()
  }, [])

  const checkRunningBenchmark = async () => {
    try {
      const prog = await api.get('/progress/benchmark')
      if (prog && (prog.status === 'running' || prog.status === 'saving')) {
        setRunning(true)
        setProgressState(prog)
      }
    } catch {}
  }

  useEffect(() => {
    let interval: any
    if (running) {
      interval = setInterval(async () => {
        try {
          const prog = await api.get('/progress/benchmark')
          if (prog) {
            setProgressState(prog)
            if (prog.status === 'completed') {
              setRunning(false)
              setRunSuccess(prog.message || 'Benchmark completato!')
              loadData()
              setTimeout(() => setRunSuccess(''), 6000)
            } else if (prog.status === 'failed') {
              setRunning(false)
              setRunError(prog.message || 'Benchmark fallito')
            }
          }
        } catch {}
      }, 800)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [running])


  const loadData = async () => {

    try {
      const [scen, res, modelsRes] = await Promise.all([
        api.get('/benchmark/scenarios'),
        api.get('/benchmark/results'),
        api.get('/settings/ollama-models').catch(() => ({ models: [] })),
      ])
      setScenarios(scen)
      setResultsData(res)
      if (modelsRes?.models?.length) {
        setOllamaModels(modelsRes.models)
        if (!modelsRes.models.includes(selectedModel)) {
          setSelectedModel(modelsRes.models[0])
        }
      }
    } catch (e) {
      console.error('Error loading benchmark data:', e)
    }
  }

  const handleRunBenchmark = async () => {
    setRunning(true)
    setRunError('')
    setRunSuccess('')
    try {
      const res = await api.post('/benchmark/run', {
        scenario: selectedScenario,
        temperature,
        provider: selectedProvider,
        model: selectedModel,
      })
      setRunSuccess(`Benchmark per ${res.model || selectedModel} completato in ${res.latency_seconds}s! (3NF: ${res.norm3_score}%)`)
      await loadData()
      setTimeout(() => setRunSuccess(''), 6000)
    } catch (e: any) {
      console.error('Benchmark execution error:', e)
      setRunError(e.message || 'Errore durante l\'esecuzione del benchmark. Verifica la connessione al provider.')
    } finally {
      setRunning(false)
    }
  }


  const handleVoteSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setVoting(true)
    setVoteSuccess('')
    try {
      await api.post('/surveys/vote', {
        schema_rating: schemaRating,
        data_rating: dataRating,
        comment,
      })
      setVoteSuccess('Voto dell\'esperto registrato con successo nel database!')
      setComment('')
      await loadData()
      setTimeout(() => setVoteSuccess(''), 4000)
    } catch (e) {
      alert('Errore nel salvataggio del voto')
    } finally {
      setVoting(false)
    }
  }

  const generateLatexTable = () => {
    if (!resultsData.results.length) return '% Nessun risultato disponibile'
    let latex = '\\begin{table}[h]\n\\centering\n\\begin{tabular}{|l|l|c|c|c|c|}\n\\hline\n'
    latex += '\\textbf{Scenario} & \\textbf{Model} & \\textbf{3NF (\\%)} & \\textbf{Rel F1} & \\textbf{Schema est.} & \\textbf{Time (s)} \\\\\n\\hline\n'
    resultsData.results.slice(0, 10).forEach((r) => {
      latex += `${r.scenario} & ${r.model} & ${r.norm3_score}\\% & ${r.relationship_f1} & ${r.schema_quality_heuristic_estimate} & ${r.latency_seconds}s \\\\\n`
    })
    latex += '\\hline\n\\end{tabular}\n\\caption{LLM Model Evaluation Results}\n\\label{tab:benchmark_results}\n\\end{table}'
    navigator.clipboard.writeText(latex)
    alert('Tabella LaTeX copiata negli appunti!')
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">Benchmark Scientifico Modelli LLM</h1>
          <p className="mt-1 text-xs text-slate-500">
            Benchmark esplorativo dello schema (3NF, Relationship F1) e feedback qualitativo. Le metriche RQ2 richiedono popolamento e ground truth e sono prodotte dal runner offline.
          </p>
        </div>
        <button
          onClick={generateLatexTable}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
        >
          📋 Copia Tabella LaTeX
        </button>
      </div>

      {/* Benchmark Control Panel */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Esegui Nuovo Test di Benchmark</h2>
        <p className="mt-1 text-xs text-slate-500">Seleziona lo scenario, il provider ed il modello specifico da testare.</p>

        {runError && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-300">
            ⚠️ {runError}
          </div>
        )}

        {runSuccess && (
          <div className="mt-4 rounded-xl border border-green-200 bg-green-50 p-4 text-xs font-semibold text-green-700 dark:border-green-900/50 dark:bg-green-950/50 dark:text-green-300">
            🎉 {runSuccess}
          </div>
        )}

        {running && (
          <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-900/50 dark:bg-blue-950/60">
            <div className="flex items-center justify-between text-xs font-semibold text-blue-700 dark:text-blue-300">
              <span className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 animate-ping rounded-full bg-blue-500"></span>
                {progressState.message || `Esecuzione benchmark per ${selectedModel}...`}
              </span>
              <span>{progressState.progress || 15}%</span>
            </div>
            <div className="mt-2.5 h-2.5 w-full overflow-hidden rounded-full bg-blue-200/60 dark:bg-blue-900/40">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-300"
                style={{ width: `${Math.max(10, progressState.progress || 15)}%` }}
              ></div>
            </div>
            {progressState.etc_seconds !== null && progressState.etc_seconds > 0 && (
              <div className="mt-2 text-right text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                ⏱️ Tempo stimato al completamento (ETC): ~{Math.round(progressState.etc_seconds)} sec
              </div>
            )}
          </div>
        )}


        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-slate-500">Scenario Gold Standard</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            >
              {scenarios.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-500">Provider IA</label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            >
              <option value="ollama">Ollama (Remoto/Locale)</option>
              <option value="google">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="groq">Groq</option>
              <option value="openrouter">OpenRouter</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-500">Modello da Valutare</label>
            {selectedProvider === 'ollama' ? (
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
              >
                {ollamaModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                placeholder="es. gemini-2.0-flash"
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
              />
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-500">Temperatura: {temperature}</label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="mt-3 w-full accent-blue-600"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleRunBenchmark}
            disabled={running}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
          >
            {running ? '🚀 Esecuzione Benchmark in corso...' : '🚀 Avvia Test Benchmark'}
          </button>
        </div>
      </div>


      {/* Automated Benchmark Results Table */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Risultati Sperimentali Quantitativi</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
            <thead className="border-b border-slate-100 bg-slate-50 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-950">
              <tr>
                <th className="px-4 py-3">Scenario</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Modello</th>
                <th className="px-4 py-3">3NF Score</th>
                <th className="px-4 py-3">Rel F1</th>
                <th className="px-4 py-3">Stima schema (non RQ2)</th>
                <th className="px-4 py-3">Latenza</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {resultsData.results.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">{r.scenario}</td>
                  <td className="px-4 py-3">{r.provider}</td>
                  <td className="px-4 py-3 font-mono text-xs text-blue-600 dark:text-blue-400">{r.model}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      {r.norm3_score}%
                    </span>
                  </td>
                  <td className="px-4 py-3 font-bold">{r.relationship_f1}</td>
                  <td className="px-4 py-3" title={r.data_metric_label}>{r.schema_quality_heuristic_estimate}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{r.latency_seconds}s</td>
                </tr>
              ))}

              {!resultsData.results.length && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-xs text-slate-400">
                    Nessun risultato di benchmark registrato. Clicca su "Esegui Test Benchmark" per iniziare.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Human Expert Evaluation & Vote Form */}
      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-6 dark:border-indigo-950 dark:bg-indigo-950/20">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">⭐ Valutazione Soggettiva dell'Utente / Esperto</h2>
        <p className="mt-1 text-xs text-slate-500">
          Valuta la qualità della generazione degli schemi e dei dati in scala Likert (1-5) come previsto dal protocollo di ricerca del paper.
        </p>

        {voteSuccess && (
          <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-100/80 p-3 text-xs font-bold text-emerald-800">
            ✓ {voteSuccess}
          </div>
        )}

        <form onSubmit={handleVoteSubmit} className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Qualità Schema Relazionale (1 = Scarso, 5 = Eccellente 3NF): {schemaRating}/5
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={schemaRating}
                onChange={(e) => setSchemaRating(parseInt(e.target.value))}
                className="mt-2 w-full accent-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Accuratezza Popolamento Dati (1 = Molti Errori, 5 = Perfetta Coerenza FK): {dataRating}/5
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={dataRating}
                onChange={(e) => setDataRating(parseInt(e.target.value))}
                className="mt-2 w-full accent-purple-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              Note & Commenti Qualitativi dell'Esperto
            </label>
            <textarea
              rows={2}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Inserisci eventuali considerazioni sulla completezza delle chiavi esterne o correttezza semantica..."
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={voting}
              className="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-bold text-white shadow hover:bg-indigo-700 disabled:opacity-50"
            >
              {voting ? 'Salvataggio Voto...' : 'Registra Voto Esperto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
