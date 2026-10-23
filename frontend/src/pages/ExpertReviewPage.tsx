import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { expertApi, ExpertSchema, EvaluationSubmission } from '../api/expertClient'
import { useAuth } from '../context/KeycloakContext'
import type { NormalizedSchema } from '../types'

const SchemaDiagram = lazy(() => import('../components/SchemaDiagram'))

function toDiagramSchema(schema: ExpertSchema): NormalizedSchema {
  const split = (ref: string) => {
    const i = ref.lastIndexOf('.')
    return i < 0 ? { table: ref, column: '' } : { table: ref.slice(0, i), column: ref.slice(i + 1) }
  }
  return {
    tables: schema.tables.map((t) => ({
      name: t.name,
      columns: t.columns.map((c) => ({
        name: c.name,
        data_type: c.data_type,
        is_primary_key: c.is_primary_key,
        is_foreign_key: c.is_foreign_key,
        is_unique: c.is_unique,
        is_not_null: c.is_not_null,
      })),
    })),
    relationships: schema.relationships.map((r) => {
      const from = split(r.from)
      const to = split(r.to)
      const type = r.type === 'many_to_many' || r.type === 'one_to_one' ? r.type : 'one_to_many'
      return { type, from_table: from.table, from_column: from.column, to_table: to.table, to_column: to.column }
    }),
  }
}

const DIMENSIONS_RUBRIC = [
  {
    key: 'd1_3nf',
    label: 'D1: Conformità 3NF (3NF Compliance)',
    desc: 'Verifica la decomposizione relazionale e assenza di ridondanza / dipendenze transitive.',
    levels: [
      { score: 1, label: '1 - Scarso', detail: 'Gravi violazioni di 2NF o 3NF; severa ridondanza dati.' },
      { score: 2, label: '2 - Sotto la media', detail: 'Presenti diverse dipendenze transitive o anomalie.' },
      { score: 3, label: '3 - Adeguato', detail: 'Nessuna violazione 2NF; lievi imperfezioni non critiche in 3NF.' },
      { score: 4, label: '4 - Buono', detail: 'Tutte le tabelle in 3NF con minime questioni estetiche.' },
      { score: 5, label: '5 - Eccellente', detail: 'Perfetta forma normale 3NF; decomposizione ottimale.' },
    ],
  },
  {
    key: 'd2_naming',
    label: 'D2: Qualità Naming (Naming Quality)',
    desc: 'Convenzioni di denominazione (snake_case), chiarezza e trasparenza semantica.',
    levels: [
      { score: 1, label: '1 - Scarso', detail: 'Stile incoerente, abbreviazioni criptiche o fuorvianti.' },
      { score: 2, label: '2 - Sotto la media', detail: 'Convenzioni miste e nomi di colonne poco chiari.' },
      { score: 3, label: '3 - Adeguato', detail: 'snake_case coerente; nomi generalmente comprensibili.' },
      { score: 4, label: '4 - Buono', detail: 'Nomi descrittivi, chiari e con ottima consistenza.' },
      { score: 5, label: '5 - Eccellente', detail: 'Nomi impeccabili ed autoesplicativi, semantica cristallina.' },
    ],
  },
  {
    key: 'd3_constraints',
    label: 'D3: Copertura Vincoli (Constraint Coverage)',
    desc: 'Specificazione corretta di chiavi primarie, foreign key, NOT NULL e vincoli UNIQUE.',
    levels: [
      { score: 1, label: '1 - Scarso', detail: 'PK mancanti, assenza di FK e di vincoli NOT NULL.' },
      { score: 2, label: '2 - Sotto la media', detail: 'Alcune PK presenti, ma FK in gran parte assenti.' },
      { score: 3, label: '3 - Adeguato', detail: 'Tutte le tabelle hanno PK; gran parte di FK e NOT NULL specificati.' },
      { score: 4, label: '4 - Buono', detail: 'Tutte le PK, FK e NOT NULL specificati accuratamente.' },
      { score: 5, label: '5 - Eccellente', detail: 'Copertura esaustiva con vincoli UNIQUE, NOT NULL e valori predefiniti.' },
    ],
  },
  {
    key: 'd4_relationships',
    label: 'D4: Accuratezza Relazioni (Relationship Accuracy)',
    desc: 'Correttezza delle cardinalità e delle chiavi esterne per l’integrità referenziale.',
    levels: [
      { score: 1, label: '1 - Scarso', detail: 'Cardinalità errate, relazioni mancanti o fantasma.' },
      { score: 2, label: '2 - Sotto la media', detail: 'Alcune relazioni corrette ma molteplici errori evidenti.' },
      { score: 3, label: '3 - Adeguato', detail: 'Maggioranza delle relazioni corretta; lievi incertezze di cardinalità.' },
      { score: 4, label: '4 - Buono', detail: 'Tutte le relazioni presenti, accurate e con tipo appropriato.' },
      { score: 5, label: '5 - Eccellente', detail: 'Relazioni perfette con semantica referenziale e vincoli ottimali.' },
    ],
  },
  {
    key: 'd5_domain',
    label: 'D5: Allineamento con il Dominio (Domain Alignment)',
    desc: 'Capacità dello schema di modellare il contesto applicativo e i requisiti informativi.',
    levels: [
      { score: 1, label: '1 - Scarso', detail: 'Lo schema non rappresenta adeguatamente il dominio descritto.' },
      { score: 2, label: '2 - Sotto la media', detail: 'Entità o attributi fondamentali del dominio sono assenti.' },
      { score: 3, label: '3 - Adeguato', detail: 'Tutte le entità chiave presenti; mancano solo dettagli secondari.' },
      { score: 4, label: '4 - Buono', detail: 'Tutte le entità e attributi presenti; ottima aderenza al dominio.' },
      { score: 5, label: '5 - Eccellente', detail: 'Supera le aspettative, modellando anche vincoli impliciti del dominio.' },
    ],
  },
]

export default function ExpertReviewPage() {
  const { username, authenticated } = useAuth()
  const [evaluatorName, setEvaluatorName] = useState<string>(() => {
    return localStorage.getItem('aidb_evaluator_name') || (authenticated && username !== 'Ospite' ? username : '')
  })
  const [nameInput, setNameInput] = useState<string>('')
  const [showNameModal, setShowNameModal] = useState<boolean>(false)

  const [schemas, setSchemas] = useState<ExpertSchema[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [saveMessage, setSaveMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [viewMode, setViewMode] = useState<'diagram' | 'visual' | 'markdown'>('diagram')
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'completed'>('all')

  // Form ratings state
  const [ratings, setRatings] = useState<{
    d1_3nf: number
    d2_naming: number
    d3_constraints: number
    d4_relationships: number
    d5_domain: number
    comment: string
  }>({
    d1_3nf: 0,
    d2_naming: 0,
    d3_constraints: 0,
    d4_relationships: 0,
    d5_domain: 0,
    comment: '',
  })

  // Load schemas from backend
  const loadSchemas = async (evaluator?: string) => {
    setLoading(true)
    try {
      const data = await expertApi.listSchemas(evaluator)
      setSchemas(data)
    } catch (err: any) {
      console.error('Errore nel caricamento degli schemi:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!evaluatorName) {
      setShowNameModal(true)
      loadSchemas()
    } else {
      loadSchemas(evaluatorName)
    }
  }, [evaluatorName])

  // Sync current schema rating into form
  const activeSchema = schemas[selectedIndex] || null
  const diagramSchema = useMemo(() => (activeSchema ? toDiagramSchema(activeSchema) : null), [activeSchema])

  useEffect(() => {
    if (activeSchema) {
      if (activeSchema.rating) {
        setRatings({
          d1_3nf: activeSchema.rating.d1_3nf,
          d2_naming: activeSchema.rating.d2_naming,
          d3_constraints: activeSchema.rating.d3_constraints,
          d4_relationships: activeSchema.rating.d4_relationships,
          d5_domain: activeSchema.rating.d5_domain,
          comment: activeSchema.rating.comment || '',
        })
      } else {
        setRatings({
          d1_3nf: 0,
          d2_naming: 0,
          d3_constraints: 0,
          d4_relationships: 0,
          d5_domain: 0,
          comment: '',
        })
      }
      setSaveMessage(null)
    }
  }, [selectedIndex, activeSchema])

  const handleSaveName = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = nameInput.trim()
    if (!trimmed) return
    localStorage.setItem('aidb_evaluator_name', trimmed)
    setEvaluatorName(trimmed)
    setShowNameModal(false)
  }

  const handleScoreChange = (dimensionKey: string, score: number) => {
    setRatings((prev) => ({ ...prev, [dimensionKey]: score }))
  }

  const isFormValid =
    ratings.d1_3nf > 0 &&
    ratings.d2_naming > 0 &&
    ratings.d3_constraints > 0 &&
    ratings.d4_relationships > 0 &&
    ratings.d5_domain > 0

  const handleSaveEvaluation = async (goToNext = false) => {
    if (!evaluatorName) {
      setShowNameModal(true)
      return
    }
    if (!activeSchema || !isFormValid) return

    setSaving(true)
    setSaveMessage(null)
    try {
      const payload: EvaluationSubmission = {
        evaluator_name: evaluatorName,
        schema_code: activeSchema.code,
        d1_3nf: ratings.d1_3nf,
        d2_naming: ratings.d2_naming,
        d3_constraints: ratings.d3_constraints,
        d4_relationships: ratings.d4_relationships,
        d5_domain: ratings.d5_domain,
        comment: ratings.comment.trim() || undefined,
      }

      await expertApi.submitEvaluation(payload)

      // Update local state
      setSchemas((prev) =>
        prev.map((s, idx) =>
          idx === selectedIndex
            ? {
                ...s,
                has_evaluated: true,
                rating: {
                  ...payload,
                  updated_at: new Date().toISOString(),
                },
              }
            : s
        )
      )

      setSaveMessage({ text: `Valutazione per ${activeSchema.code} salvata con successo!`, type: 'success' })

      if (goToNext && selectedIndex < schemas.length - 1) {
        setSelectedIndex(selectedIndex + 1)
      }
    } catch (err: any) {
      setSaveMessage({ text: err?.message || 'Errore durante il salvataggio della valutazione.', type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const completedCount = schemas.filter((s) => s.has_evaluated).length
  const totalCount = schemas.length
  const completionPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  const filteredSchemas = schemas.filter((s) => {
    if (filterMode === 'pending') return !s.has_evaluated
    if (filterMode === 'completed') return s.has_evaluated
    return true
  })

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-600 dark:text-amber-400">
                Studio RQ1 // Expert Review
              </span>
              <span className="rounded-md bg-blue-500/10 px-2.5 py-1 text-xs font-semibold text-blue-600 dark:text-blue-400">
                Doppio Cieco (Condition-Blind)
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
              Valutazione Qualitativa degli Schemi di Database
            </h1>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Valuta ciascuno schema anonimo secondo le 5 dimensioni metriche del protocollo di ricerca (Scala Likert 1-5).
            </p>
          </div>

          {/* Evaluator identity badge */}
          <div className="flex flex-col items-start gap-2 rounded-xl border border-slate-200/80 bg-slate-50 p-3.5 sm:items-end dark:border-slate-800 dark:bg-slate-800/50">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500 dark:text-slate-400">Esperto Valutatore:</span>
              <span className="font-bold text-slate-900 dark:text-white">
                {evaluatorName ? evaluatorName : 'Non impostato'}
              </span>
              <button
                onClick={() => {
                  setNameInput(evaluatorName)
                  setShowNameModal(true)
                }}
                className="ml-1 text-[11px] font-semibold text-blue-600 hover:underline dark:text-blue-400"
              >
                (Cambia)
              </button>
            </div>

            {/* Progress bar */}
            <div className="w-full sm:w-48">
              <div className="flex justify-between text-[11px] font-medium text-slate-600 dark:text-slate-300">
                <span>Progresso</span>
                <span>
                  {completedCount}/{totalCount} ({completionPercent}%)
                </span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-300"
                  style={{ width: `${completionPercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Schema Navigation Carousel / Bar */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Schemi:</span>
            <div className="flex gap-1">
              <button
                onClick={() => setFilterMode('all')}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                  filterMode === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                }`}
              >
                Tutti ({totalCount})
              </button>
              <button
                onClick={() => setFilterMode('pending')}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                  filterMode === 'pending'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                }`}
              >
                Da completare ({totalCount - completedCount})
              </button>
              <button
                onClick={() => setFilterMode('completed')}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                  filterMode === 'completed'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                }`}
              >
                Completati ({completedCount})
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedIndex((prev) => Math.max(0, prev - 1))}
              disabled={selectedIndex === 0}
              className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              ◀ Precedente
            </button>
            <span className="text-xs font-bold text-slate-500">
              {selectedIndex + 1} di {schemas.length}
            </span>
            <button
              onClick={() => setSelectedIndex((prev) => Math.min(schemas.length - 1, prev + 1))}
              disabled={selectedIndex >= schemas.length - 1}
              className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Successivo ▶
            </button>
          </div>
        </div>

        {/* Horizontal scroll pills */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {filteredSchemas.map((schema) => {
            const actualIdx = schemas.findIndex((s) => s.code === schema.code)
            const isSelected = actualIdx === selectedIndex
            return (
              <button
                key={schema.code}
                onClick={() => setSelectedIndex(actualIdx)}
                className={`group relative flex min-w-[72px] flex-col items-center justify-center rounded-xl border p-2 text-center transition-all ${
                  isSelected
                    ? 'border-blue-600 bg-blue-50 ring-2 ring-blue-500/20 dark:bg-blue-950/40'
                    : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className={`text-xs font-black ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-slate-800 dark:text-slate-200'}`}>
                    {schema.code}
                  </span>
                  {schema.has_evaluated ? (
                    <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-white" title="Valutato">
                      ✓
                    </span>
                  ) : (
                    <span className="h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-700" title="In attesa" />
                  )}
                </div>
                <span className="mt-1 text-[10px] text-slate-400">
                  {schema.table_count} tab.
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Split Grid: Schema Viewer (Left) + Rubric Form (Right) */}
      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          Caricamento schemi in corso...
        </div>
      ) : activeSchema ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* LEFT: Schema Viewer (7 cols) */}
          <div className="space-y-4 lg:col-span-7">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-600 text-xs font-black text-white">
                    {activeSchema.code}
                  </span>
                  <div>
                    <h2 className="text-base font-bold text-slate-900 dark:text-white">
                      {activeSchema.title}
                    </h2>
                    <span className="text-[11px] text-slate-400">
                      {activeSchema.table_count} Tabelle · {activeSchema.column_count} Colonne · {activeSchema.relationship_count} Relazioni
                    </span>
                  </div>
                </div>

                {/* View Mode Toggle */}
                <div className="flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-800">
                  <button
                    onClick={() => setViewMode('diagram')}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                      viewMode === 'diagram'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                    }`}
                  >
                    Diagramma
                  </button>
                  <button
                    onClick={() => setViewMode('visual')}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                      viewMode === 'visual'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                    }`}
                  >
                    Visuale Tabelle
                  </button>
                  <button
                    onClick={() => setViewMode('markdown')}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                      viewMode === 'markdown'
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                    }`}
                  >
                    Markdown Originale
                  </button>
                </div>
              </div>

              {/* Description box */}
              {activeSchema.description && (
                <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-xs text-blue-900 dark:border-blue-900/40 dark:bg-blue-950/30 dark:text-blue-200">
                  <strong className="font-bold">Descrizione del Dominio: </strong>
                  {activeSchema.description}
                </div>
              )}

              {/* Schema Display */}
              <div className="mt-4">
                {viewMode === 'diagram' ? (
                  <Suspense fallback={<div className="py-12 text-center text-sm text-slate-500">Caricamento diagramma…</div>}>
                    {diagramSchema && <SchemaDiagram key={activeSchema.code} schema={diagramSchema} />}
                  </Suspense>
                ) : viewMode === 'visual' ? (
                  <div className="space-y-4">
                    {activeSchema.tables.map((table) => (
                      <div
                        key={table.name}
                        className="overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50/50 shadow-xs dark:border-slate-800 dark:bg-slate-950/40"
                      >
                        <div className="flex items-center justify-between border-b border-slate-200/70 bg-slate-100/70 px-3.5 py-2 dark:border-slate-800 dark:bg-slate-800/40">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-black text-slate-700 dark:text-slate-300">
                              TABLE
                            </span>
                            <span className="font-mono text-sm font-bold text-blue-700 dark:text-blue-400">
                              {table.name}
                            </span>
                          </div>
                          <span className="text-[11px] font-medium text-slate-400">
                            {table.columns.length} colonne
                          </span>
                        </div>

                        <div className="divide-y divide-slate-100 dark:divide-slate-800/60">
                          {table.columns.map((col) => (
                            <div
                              key={col.name}
                              className="flex items-center justify-between px-3.5 py-2 text-xs hover:bg-slate-100/40 dark:hover:bg-slate-800/20"
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                                  {col.name}
                                </span>
                                <span className="rounded bg-slate-200/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                                  {col.data_type}
                                </span>
                              </div>

                              <div className="flex flex-wrap items-center gap-1.5">
                                {col.is_primary_key && (
                                  <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                                    🔑 PK
                                  </span>
                                )}
                                {col.is_foreign_key && (
                                  <span
                                    className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300"
                                    title={`Riferimento a ${col.foreign_key_target}`}
                                  >
                                    🔗 FK {col.foreign_key_target ? `→ ${col.foreign_key_target}` : ''}
                                  </span>
                                )}
                                {col.is_not_null && (
                                  <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-800 dark:bg-rose-950/60 dark:text-rose-300">
                                    NN
                                  </span>
                                )}
                                {col.is_unique && (
                                  <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
                                    UQ
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}

                    {/* Relationships */}
                    {activeSchema.relationships.length > 0 && (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                        <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                          Relazioni ({activeSchema.relationships.length})
                        </h4>
                        <div className="space-y-1.5">
                          {activeSchema.relationships.map((rel, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 font-mono text-xs shadow-2xs dark:bg-slate-900"
                            >
                              <span className="font-semibold text-blue-600 dark:text-blue-400">{rel.from}</span>
                              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-800">
                                {rel.type || 'rel'}
                              </span>
                              <span className="font-semibold text-indigo-600 dark:text-indigo-400">{rel.to}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <pre className="max-h-[600px] overflow-auto rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-200 dark:border-slate-800">
                    {activeSchema.raw_markdown}
                  </pre>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Rubric Evaluation Form (5 cols) */}
          <div className="space-y-4 lg:col-span-5">
            <div className="sticky top-20 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="border-b border-slate-100 pb-3 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Scheda di Valutazione
                  </h3>
                  {activeSchema.has_evaluated && (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                      ✓ Già Valutato
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Assegna un punteggio da 1 a 5 per ogni dimensione definita nel protocollo.
                </p>
              </div>

              {/* Notification Banner */}
              {saveMessage && (
                <div
                  className={`mt-4 rounded-xl p-3 text-xs font-semibold ${
                    saveMessage.type === 'success'
                      ? 'border border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-200'
                      : 'border border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200'
                  }`}
                >
                  {saveMessage.text}
                </div>
              )}

              {/* Rubric Dimensions */}
              <div className="mt-4 max-h-[580px] space-y-4 overflow-y-auto pr-1">
                {DIMENSIONS_RUBRIC.map((dim) => {
                  const currentScore = (ratings as any)[dim.key] || 0
                  const selectedLevel = dim.levels.find((l) => l.score === currentScore)

                  return (
                    <div
                      key={dim.key}
                      className="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/30"
                    >
                      <div className="mb-1.5 flex items-start justify-between">
                        <div>
                          <label className="text-xs font-bold text-slate-900 dark:text-slate-100">
                            {dim.label}
                          </label>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400">{dim.desc}</p>
                        </div>
                        {currentScore > 0 && (
                          <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-black text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                            {currentScore}/5
                          </span>
                        )}
                      </div>

                      {/* 1-5 Score buttons */}
                      <div className="mt-2 grid grid-cols-5 gap-1.5">
                        {[1, 2, 3, 4, 5].map((val) => {
                          const active = currentScore === val
                          return (
                            <button
                              key={val}
                              type="button"
                              onClick={() => handleScoreChange(dim.key, val)}
                              className={`flex flex-col items-center justify-center rounded-lg border py-2 text-xs font-bold transition-all ${
                                active
                                  ? 'border-blue-600 bg-blue-600 text-white shadow-xs'
                                  : 'border-slate-200 bg-white text-slate-700 hover:border-blue-400 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
                              }`}
                            >
                              <span>{val}</span>
                            </button>
                          )
                        })}
                      </div>

                      {/* Detail text of the selected score */}
                      {selectedLevel && (
                        <p className="mt-2 rounded-lg bg-white/80 p-2 text-[11px] text-slate-600 dark:bg-slate-900/60 dark:text-slate-300">
                          <strong className="font-semibold text-slate-800 dark:text-slate-200">
                            {selectedLevel.label}:{' '}
                          </strong>
                          {selectedLevel.detail}
                        </p>
                      )}
                    </div>
                  )
                })}

                {/* Qualitative comment */}
                <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/30">
                  <label htmlFor="comment-input" className="block text-xs font-bold text-slate-900 dark:text-slate-100">
                    Note e commenti dell'esperto (opzionale)
                  </label>
                  <p className="mb-2 text-[11px] text-slate-500">
                    Consigliato per motivare eventuali criticità riscontrate o voti inferiori a 3.
                  </p>
                  <textarea
                    id="comment-input"
                    rows={3}
                    value={ratings.comment}
                    onChange={(e) => setRatings((prev) => ({ ...prev, comment: e.target.value }))}
                    placeholder="Es. Mancano foreign key per le multe, denominazione categorie poco coerente..."
                    className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-hidden dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Form Action buttons */}
              <div className="mt-4 space-y-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                {!isFormValid && (
                  <p className="text-center text-[11px] font-medium text-amber-600 dark:text-amber-400">
                    ⚠️ Assegna un voto a tutte e 5 le dimensioni per salvare la valutazione.
                  </p>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => handleSaveEvaluation(false)}
                    disabled={!isFormValid || saving}
                    className="flex-1 rounded-xl bg-slate-800 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-slate-900 disabled:opacity-50 dark:bg-slate-700 dark:hover:bg-slate-600"
                  >
                    {saving ? 'Salvataggio...' : 'Salva'}
                  </button>
                  <button
                    onClick={() => handleSaveEvaluation(true)}
                    disabled={!isFormValid || saving}
                    className="flex-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
                  >
                    {saving ? 'Salvataggio...' : 'Salva e Prossimo ➔'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Name Input Modal */}
      {showNameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-blue-100 text-xl text-blue-600 dark:bg-blue-950 dark:text-blue-400">
              ✍️
            </div>
            <h2 className="mt-3 text-center text-lg font-bold text-slate-900 dark:text-white">
              Identificativo Valutatore
            </h2>
            <p className="mt-1 text-center text-xs text-slate-500">
              Inserisci il tuo nome o codice identificativo (es. <em>Esperto 1</em>, <em>Prof. Rossi</em>).
              Questo consentirà di salvare le tue valutazioni e riprenderle in qualsiasi momento.
            </p>

            <form onSubmit={handleSaveName} className="mt-4 space-y-3">
              <input
                type="text"
                required
                autoFocus
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder="Nome o identificativo esperto..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />

              <div className="flex gap-2 pt-2">
                {evaluatorName && (
                  <button
                    type="button"
                    onClick={() => setShowNameModal(false)}
                    className="flex-1 rounded-xl border border-slate-200 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    Annulla
                  </button>
                )}
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-xs font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700"
                >
                  Continua alla Valutazione
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
