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
      setVoteSuccess('Voto dell\'esperto registrato.')
      setComment('')
      await loadData()
      setTimeout(() => setVoteSuccess(''), 4000)
    } catch (e) {
      setRunError('Non siamo riusciti a salvare il voto. Riprova.')
    } finally {
      setVoting(false)
    }
  }

  const generateLatexTable = () => {
    if (!resultsData.results.length) return '% Nessun risultato disponibile'
    let latex = '\\begin{table}[h]\n\\centering\n\\begin{tabular}{|l|l|c|c|c|c|}\n\\hline\n'
    latex += '\\textbf{Scenario} & \\textbf{Modello} & \\textbf{3NF (\\%)} & \\textbf{Rel F1} & \\textbf{Prec. dati} & \\textbf{Tempo (s)} \\\\\n\\hline\n'
    resultsData.results.slice(0, 10).forEach((r) => {
      latex += `${r.scenario} & ${r.model} & ${r.norm3_score}\\% & ${r.relationship_f1} & ${r.cell_precision} & ${r.latency_seconds}s \\\\\n`
    })
    latex += '\\hline\n\\end{tabular}\n\\caption{Risultati della valutazione dei modelli IA}\n\\label{tab:benchmark_results}\n\\end{table}'
    navigator.clipboard.writeText(latex)
    alert('Tabella LaTeX copiata negli appunti!')
  }

  const rows = resultsData.results
  const avg = (key: string) => (rows.length ? rows.reduce((sum, r) => sum + (Number(r[key]) || 0), 0) / rows.length : null)
  const kpis = [
    { label: 'Esecuzioni registrate', value: String(rows.length), hint: 'nel database dei risultati' },
    { label: 'Schemi in 3NF', value: avg('norm3_score') === null ? '—' : `${Math.round(avg('norm3_score')!)}%`, hint: 'media delle esecuzioni' },
    { label: 'Tempo medio', value: avg('latency_seconds') === null ? '—' : `${avg('latency_seconds')!.toFixed(1)} s`, hint: 'dal documento allo schema' },
    { label: 'Voti degli esperti', value: String(resultsData.votes?.length ?? 0), hint: 'valutazioni soggettive' },
  ]
  const selectCls = 'field mt-1'
  const labelCls = 'block font-headline text-[13px] font-semibold'

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Benchmark</h1>
          <p className="mt-1.5 max-w-xl text-base text-tecnia-muted dark:text-slate-400">
            Quanto bene i modelli costruiscono schemi e dati. Ogni numero rimanda a un'esecuzione registrata.
          </p>
        </div>
        <button onClick={generateLatexTable} className="secondary-button">
          <span className="material-symbols-outlined" aria-hidden="true">content_copy</span>Copia tabella LaTeX
        </button>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="glass flex flex-col gap-1.5 p-5">
            <span className="text-[13px] text-tecnia-muted dark:text-slate-400">{k.label}</span>
            <b className="font-headline text-3xl">{k.value}</b>
            <span className="text-xs text-tecnia-muted dark:text-slate-400">{k.hint}</span>
          </div>
        ))}
      </div>

      <section className="glass p-6" aria-labelledby="run-title">
        <h2 id="run-title" className="text-lg font-bold">Esegui un nuovo test</h2>
        <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">Scegli lo scenario di riferimento, il fornitore e il modello da valutare.</p>

        {runError && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700 dark:border-red-900/50 dark:bg-red-950/50 dark:text-red-300">{runError}</div>}
        {runSuccess && <div role="status" className="mt-4 rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-semibold text-tecnia-ok dark:border-green-900/50 dark:bg-green-950/50 dark:text-green-300">{runSuccess}</div>}

        {running && (
          <div className="mt-4 rounded-2xl border border-orange-200 bg-orange-50/60 p-4 dark:border-orange-900/50 dark:bg-orange-950/40" role="status">
            <div className="flex items-center justify-between text-sm font-semibold text-tecnia-primary dark:text-orange-300">
              <span className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 animate-ping rounded-full bg-orange-500"></span>
                {progressState.message || `Test in corso per ${selectedModel}…`}
              </span>
              <span>{progressState.progress || 15}%</span>
            </div>
            <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-orange-100 dark:bg-orange-900/40">
              <div className="h-full rounded-full bg-gradient-to-r from-[#ff6b00] to-[#fe3ac6] transition-all duration-300" style={{ width: `${Math.max(10, progressState.progress || 15)}%` }}></div>
            </div>
            {progressState.etc_seconds !== null && progressState.etc_seconds > 0 && (
              <div className="mt-2 text-right text-xs font-semibold text-tecnia-muted dark:text-slate-400">Tempo stimato: circa {Math.round(progressState.etc_seconds)} secondi</div>
            )}
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="bm-scenario" className={labelCls}>Scenario di riferimento</label>
            <select id="bm-scenario" value={selectedScenario} onChange={(e) => setSelectedScenario(e.target.value)} className={selectCls}>
              {scenarios.map((s) => <option key={s.key} value={s.key}>{s.title}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="bm-provider" className={labelCls}>Fornitore IA</label>
            <select id="bm-provider" value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)} className={selectCls}>
              <option value="ollama">Ollama (remoto o locale)</option>
              <option value="google">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="groq">Groq</option>
              <option value="openrouter">OpenRouter</option>
            </select>
          </div>
          <div>
            <label htmlFor="bm-model" className={labelCls}>Modello da valutare</label>
            {selectedProvider === 'ollama' ? (
              <select id="bm-model" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} className={selectCls}>
                {ollamaModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            ) : (
              <input id="bm-model" type="text" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} placeholder="es. gemini-2.0-flash" className={selectCls} />
            )}
          </div>
          <div>
            <label htmlFor="bm-temp" className={labelCls}>Temperatura: {temperature}</label>
            <input id="bm-temp" type="range" min="0.0" max="1.0" step="0.05" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} className="mt-3 w-full accent-orange-600" />
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <button onClick={handleRunBenchmark} disabled={running} className="primary-button">
            {running ? 'Test in corso…' : 'Avvia il test'}
          </button>
        </div>
      </section>

      <section className="glass py-2" aria-labelledby="res-title">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 pb-2 pt-4">
          <h2 id="res-title" className="text-lg font-bold">Risultati sperimentali</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-tecnia-muted">
                <th className="px-5 py-2 font-semibold">Scenario</th>
                <th className="px-3 py-2 font-semibold">Fornitore</th>
                <th className="px-3 py-2 font-semibold">Modello</th>
                <th className="px-3 py-2 font-semibold">Schema 3NF</th>
                <th className="px-3 py-2 font-semibold">Relazioni (F1)</th>
                <th className="px-3 py-2 font-semibold">Precisione dati</th>
                <th className="px-5 py-2 font-semibold">Tempo</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-tecnia-line/40">
                  <td className="px-5 py-3 font-headline font-bold">{r.scenario}</td>
                  <td className="px-3 py-3">{r.provider}</td>
                  <td className="px-3 py-3 font-mono text-xs text-tecnia-primary">{r.model}</td>
                  <td className="px-3 py-3"><span className="tag text-tecnia-ok">{r.norm3_score}%</span></td>
                  <td className="px-3 py-3 font-semibold">{r.relationship_f1}</td>
                  <td className="px-3 py-3">{r.cell_precision}</td>
                  <td className="px-5 py-3 text-xs text-tecnia-muted">{r.latency_seconds}s</td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={7} className="px-5 py-8 text-center text-sm text-tecnia-muted">Nessuna esecuzione registrata. Avvia il primo test qui sopra: nessun numero compare senza un'esecuzione alle spalle.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="glass p-6" aria-labelledby="vote-title">
        <h2 id="vote-title" className="text-lg font-bold">Valutazione dell'esperto</h2>
        <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">
          Dai un giudizio da 1 a 5 sulla qualità di schema e dati, come previsto dal protocollo di ricerca.
        </p>
        {voteSuccess && <div role="status" className="mt-4 rounded-xl border border-green-200 bg-green-50 p-3 text-sm font-semibold text-tecnia-ok">{voteSuccess}</div>}
        <form onSubmit={handleVoteSubmit} className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="bm-schema" className={labelCls}>Schema relazionale (1 scarso, 5 eccellente): {schemaRating}/5</label>
              <input id="bm-schema" type="range" min="1" max="5" value={schemaRating} onChange={(e) => setSchemaRating(parseInt(e.target.value))} className="mt-2 w-full accent-orange-600" />
            </div>
            <div>
              <label htmlFor="bm-data" className={labelCls}>Accuratezza dei dati (1 molti errori, 5 coerenza perfetta): {dataRating}/5</label>
              <input id="bm-data" type="range" min="1" max="5" value={dataRating} onChange={(e) => setDataRating(parseInt(e.target.value))} className="mt-2 w-full accent-fuchsia-700" />
            </div>
          </div>
          <div>
            <label htmlFor="bm-comment" className={labelCls}>Note e commenti</label>
            <textarea id="bm-comment" rows={2} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Annota completezza delle chiavi esterne, correttezza semantica, dubbi…" className="field mt-1" />
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={voting} className="primary-button">{voting ? 'Salvataggio…' : 'Registra il voto'}</button>
          </div>
        </form>
      </section>
    </div>
  )
}
