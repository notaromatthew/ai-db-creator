import React, { useEffect, useState } from 'react'
import { expertApi, AdminDashboardData } from '../api/expertClient'

export default function AdminEvaluationsPage() {
  const [adminKey, setAdminKey] = useState<string>(() => sessionStorage.getItem('aidb_admin_key') || '')
  const [keyInput, setKeyInput] = useState<string>('')
  const [authError, setAuthError] = useState<string>('')
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [verifying, setVerifying] = useState<boolean>(false)

  const [data, setData] = useState<AdminDashboardData | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')

  // Table filters
  const [filterEvaluator, setFilterEvaluator] = useState<string>('all')
  const [filterDataset, setFilterDataset] = useState<string>('all')
  const [filterCondition, setFilterCondition] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState<string>('')

  const checkAuthAndLoad = async (key: string) => {
    setVerifying(true)
    setAuthError('')
    try {
      await expertApi.verifyAdminKey(key)
      setIsAuthenticated(true)
      sessionStorage.setItem('aidb_admin_key', key)
      loadDashboard(key)
    } catch (err: any) {
      setIsAuthenticated(false)
      sessionStorage.removeItem('aidb_admin_key')
      setAuthError(err?.message || 'Password amministratore non corretta.')
    } finally {
      setVerifying(false)
    }
  }

  const loadDashboard = async (key: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await expertApi.getAdminDashboard(key)
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Impossibile recuperare i dati della dashboard.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (adminKey) {
      checkAuthAndLoad(adminKey)
    }
  }, [])

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyInput.trim()) return
    setAdminKey(keyInput.trim())
    checkAuthAndLoad(keyInput.trim())
  }

  const handleLogout = () => {
    sessionStorage.removeItem('aidb_admin_key')
    setAdminKey('')
    setIsAuthenticated(false)
    setData(null)
  }

  // Filtered evaluations
  const filteredEvaluations = (data?.evaluations || []).filter((item) => {
    if (filterEvaluator !== 'all' && item.evaluator_name !== filterEvaluator) return false
    if (filterDataset !== 'all' && item.dataset !== filterDataset) return false
    if (filterCondition !== 'all' && item.condition !== filterCondition) return false
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase()
      const matchCode = item.schema_code.toLowerCase().includes(q)
      const matchName = item.evaluator_name.toLowerCase().includes(q)
      const matchComment = item.comment.toLowerCase().includes(q)
      if (!matchCode && !matchName && !matchComment) return false
    }
    return true
  })

  // Login view if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="mx-auto my-12 max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-amber-50 text-2xl text-amber-600 dark:bg-amber-950/50 dark:text-amber-400">
          🛡️
        </div>
        <h2 className="mt-4 text-center text-xl font-bold text-slate-900 dark:text-white">
          Accesso Amministrazione RQ1
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Inserisci la chiave o password amministratore per visionare le valutazioni in chiaro ed esportare i risultati.
        </p>

        {authError && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
            {authError}
          </div>
        )}

        <form onSubmit={handleLogin} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-300">
              Chiave Amministratore
            </label>
            <input
              type="password"
              required
              autoFocus
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="Inserisci password..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
            <p className="mt-1 text-[11px] text-slate-400">
              Predefinita in sviluppo: <code className="font-mono text-slate-600 dark:text-slate-300">admin123</code> (configurabile in .env)
            </p>
          </div>

          <button
            type="submit"
            disabled={verifying}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-xs font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
          >
            {verifying ? 'Verifica in corso...' : 'Accedi al Pannello Risultati'}
          </button>
        </form>
      </div>
    )
  }

  const exportUrl = expertApi.getExportCsvUrl(adminKey)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-purple-500/10 px-2.5 py-1 text-xs font-bold text-purple-600 dark:text-purple-400">
                Pannello Amministratore // Ricerca
              </span>
              <span className="rounded-md bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                Unblinded View Attiva
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
              Valutazioni Esperti RQ1 — Risultati & Analisi
            </h1>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Visiona le schede valutate dagli esperti unblended con dataset, condizione (Baseline vs Full LLM) e run.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => loadDashboard(adminKey)}
              disabled={loading}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              🔄 Aggiorna Dati
            </button>

            <a
              href={exportUrl}
              download="expert_ratings_export.csv"
              className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:from-emerald-700 hover:to-teal-700"
            >
              ⬇️ Esporta CSV Valutazioni
            </a>

            <button
              onClick={handleLogout}
              className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Esci Admin
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          Caricamento dati di valutazione in corso...
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs font-semibold text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* KPI Stat Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Valutazioni Totali</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-black text-slate-900 dark:text-white">
                  {data.total_evaluations}
                </span>
                <span className="text-xs text-slate-400">su 30 schemi</span>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Esperti Coinvolti</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-black text-blue-600 dark:text-blue-400">
                  {data.unique_evaluators_count}
                </span>
                <span className="text-xs text-slate-400">esperti unici</span>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Punteggio Medio Globale</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-black text-emerald-600 dark:text-emerald-400">
                  {data.overall_means.overall > 0 ? `${data.overall_means.overall} / 5` : '—'}
                </span>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Copertura Schemi</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-black text-purple-600 dark:text-purple-400">
                  {data.schema_summary.filter((s) => s.evaluations_count > 0).length} / {data.total_schemas}
                </span>
                <span className="text-xs text-slate-400">con almeno 1 voto</span>
              </div>
            </div>
          </div>

          {/* RQ1 Condition Comparison: Baseline vs Full LLM */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-8 dark:border-slate-800 dark:bg-slate-900">
              <div className="border-b border-slate-100 pb-3 dark:border-slate-800">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  RQ1: Confronto Condizioni — Baseline vs Full LLM
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Confronto delle medie dei punteggi attribuiti dagli esperti sulle 5 dimensioni (Scala Likert 1-5).
                </p>
              </div>

              <div className="mt-4 space-y-4">
                {[
                  { key: 'd1_3nf', label: 'D1: Conformità 3NF' },
                  { key: 'd2_naming', label: 'D2: Qualità Naming' },
                  { key: 'd3_constraints', label: 'D3: Copertura Vincoli' },
                  { key: 'd4_relationships', label: 'D4: Accuratezza Relazioni' },
                  { key: 'd5_domain', label: 'D5: Allineamento Dominio' },
                  { key: 'overall', label: 'Media Complessiva' },
                ].map((dim) => {
                  const bScore = (data.condition_comparison.baseline as any)[dim.key] || 0
                  const fScore = (data.condition_comparison.full_llm as any)[dim.key] || 0
                  const diff = Math.round((fScore - bScore) * 100) / 100

                  return (
                    <div key={dim.key} className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-800/20">
                      <div className="mb-2 flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-800 dark:text-slate-200">{dim.label}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-slate-500">
                            Baseline: <strong className="text-slate-800 dark:text-slate-200">{bScore || '—'}</strong>
                          </span>
                          <span className="text-slate-500">
                            Full LLM: <strong className="text-blue-600 dark:text-blue-400">{fScore || '—'}</strong>
                          </span>
                          {bScore > 0 && fScore > 0 && (
                            <span
                              className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                diff >= 0
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                              }`}
                            >
                              {diff >= 0 ? `+${diff}` : `${diff}`}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Visual comparative bars */}
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="w-16 text-[10px] text-slate-500">Baseline</span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                            <div
                              className="h-full rounded-full bg-slate-500"
                              style={{ width: `${(bScore / 5) * 100}%` }}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-16 text-[10px] text-slate-500">Full LLM</span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                            <div
                              className="h-full rounded-full bg-blue-600"
                              style={{ width: `${(fScore / 5) * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Evaluator Progress Column */}
            <div className="space-y-6 lg:col-span-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Progresso per Esperto
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Avanzamento dei singoli revisori rispetto ai 30 schemi.
                </p>

                <div className="mt-4 space-y-3">
                  {data.evaluator_progress.length === 0 ? (
                    <p className="text-xs text-slate-400">Nessuna valutazione registrata al momento.</p>
                  ) : (
                    data.evaluator_progress.map((ev) => (
                      <div key={ev.evaluator_name} className="rounded-xl border border-slate-100 p-3 dark:border-slate-800">
                        <div className="flex justify-between text-xs font-bold text-slate-800 dark:text-slate-200">
                          <span>{ev.evaluator_name}</span>
                          <span>
                            {ev.completed} / {ev.total} ({ev.progress_percent}%)
                          </span>
                        </div>
                        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-600"
                            style={{ width: `${ev.progress_percent}%` }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Dataset Breakdown */}
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Medie per Dataset
                </h3>
                <div className="mt-3 divide-y divide-slate-100 text-xs dark:divide-slate-800">
                  {Object.entries(data.dataset_comparison).map(([ds, scores]) => (
                    <div key={ds} className="flex items-center justify-between py-2">
                      <span className="font-semibold uppercase text-slate-700 dark:text-slate-300">
                        {ds}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">{scores.count} schede</span>
                        <span className="rounded-md bg-blue-100 px-2 py-0.5 font-bold text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                          {scores.overall > 0 ? `${scores.overall} / 5` : '—'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Full Evaluations Data Table */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col gap-4 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Registro Dettagliato delle Valutazioni ({filteredEvaluations.length})
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Tutte le schede valutate con metadati unblinded (Dataset, Condizione, Run) e commenti.
                </p>
              </div>

              {/* Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="Cerca esperto, schema o commento..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs focus:border-blue-500 focus:bg-white focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />

                <select
                  value={filterEvaluator}
                  onChange={(e) => setFilterEvaluator(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="all">Tutti gli Esperti</option>
                  {data.evaluator_progress.map((ev) => (
                    <option key={ev.evaluator_name} value={ev.evaluator_name}>
                      {ev.evaluator_name}
                    </option>
                  ))}
                </select>

                <select
                  value={filterCondition}
                  onChange={(e) => setFilterCondition(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="all">Tutte le Condizioni</option>
                  <option value="baseline">Baseline</option>
                  <option value="full_llm">Full LLM</option>
                </select>

                <select
                  value={filterDataset}
                  onChange={(e) => setFilterDataset(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="all">Tutti i Dataset</option>
                  <option value="hospital">Hospital</option>
                  <option value="library">Library</option>
                  <option value="university">University</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                    <th className="py-2.5 px-3 font-semibold">Esperto</th>
                    <th className="py-2.5 px-3 font-semibold">Codice</th>
                    <th className="py-2.5 px-3 font-semibold">Dataset</th>
                    <th className="py-2.5 px-3 font-semibold">Condizione</th>
                    <th className="py-2.5 px-3 font-semibold">Run</th>
                    <th className="py-2.5 px-2 font-semibold text-center" title="D1: 3NF Compliance">D1</th>
                    <th className="py-2.5 px-2 font-semibold text-center" title="D2: Naming Quality">D2</th>
                    <th className="py-2.5 px-2 font-semibold text-center" title="D3: Constraint Coverage">D3</th>
                    <th className="py-2.5 px-2 font-semibold text-center" title="D4: Relationship Accuracy">D4</th>
                    <th className="py-2.5 px-2 font-semibold text-center" title="D5: Domain Alignment">D5</th>
                    <th className="py-2.5 px-2 font-semibold text-center">Media</th>
                    <th className="py-2.5 px-3 font-semibold">Commento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {filteredEvaluations.length === 0 ? (
                    <tr>
                      <td colSpan={12} className="py-8 text-center text-slate-400">
                        Nessuna valutazione corrispondente ai filtri selezionati.
                      </td>
                    </tr>
                  ) : (
                    filteredEvaluations.map((ev) => (
                      <tr key={ev.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20">
                        <td className="py-2.5 px-3 font-bold text-slate-900 dark:text-slate-100">
                          {ev.evaluator_name}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-blue-600 dark:text-blue-400">
                          {ev.schema_code}
                        </td>
                        <td className="py-2.5 px-3 font-medium capitalize text-slate-600 dark:text-slate-300">
                          {ev.dataset}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                              ev.condition === 'full_llm'
                                ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                                : 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                            }`}
                          >
                            {ev.condition}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">{ev.run}</td>
                        <td className="py-2.5 px-2 text-center font-bold">{ev.d1_3nf}</td>
                        <td className="py-2.5 px-2 text-center font-bold">{ev.d2_naming}</td>
                        <td className="py-2.5 px-2 text-center font-bold">{ev.d3_constraints}</td>
                        <td className="py-2.5 px-2 text-center font-bold">{ev.d4_relationships}</td>
                        <td className="py-2.5 px-2 text-center font-bold">{ev.d5_domain}</td>
                        <td className="py-2.5 px-2 text-center">
                          <span className="rounded bg-emerald-100 px-1.5 py-0.5 font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                            {ev.average_score}
                          </span>
                        </td>
                        <td className="max-w-xs truncate py-2.5 px-3 text-slate-600 dark:text-slate-300" title={ev.comment}>
                          {ev.comment || '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
