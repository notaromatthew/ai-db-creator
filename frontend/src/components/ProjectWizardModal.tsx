import React, { useState } from 'react'

interface ProjectWizardModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateProject: (name: string, prompt: string, mode: 'quick' | 'wizard') => void
}

export const ProjectWizardModal: React.FC<ProjectWizardModalProps> = ({
  isOpen,
  onClose,
  onCreateProject,
}) => {
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const [mode, setMode] = useState<'quick' | 'wizard'>('wizard')
  const [step, setStep] = useState(1)

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onCreateProject(name.trim(), prompt.trim(), mode)
    setName('')
    setPrompt('')
    setStep(1)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Crea Nuovo Progetto Database</h2>
            <p className="text-xs text-slate-500">Scegli la modalità di creazione che preferisci</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-white"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* Choice Cards */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setMode('quick')}
              className={`rounded-xl border p-4 text-left transition-all ${
                mode === 'quick'
                  ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20 dark:border-blue-500 dark:bg-blue-950/40'
                  : 'border-slate-200 bg-slate-50 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900'
              }`}
            >
              <div className="text-2xl">⚡</div>
              <div className="mt-2 font-bold text-slate-900 dark:text-white">Flusso Rapido</div>
              <div className="mt-1 text-xs text-slate-500">
                Inserisci prompt e documenti direttamente per utenti esperti.
              </div>
            </button>

            <button
              type="button"
              onClick={() => setMode('wizard')}
              className={`rounded-xl border p-4 text-left transition-all ${
                mode === 'wizard'
                  ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 dark:border-indigo-500 dark:bg-indigo-950/40'
                  : 'border-slate-200 bg-slate-50 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900'
              }`}
            >
              <div className="text-2xl">🧙‍♂️</div>
              <div className="mt-2 font-bold text-slate-900 dark:text-white">Wizard Guidato</div>
              <div className="mt-1 text-xs text-slate-500">
                Percorso passo-passo assistito per guidare l'utente non esperto.
              </div>
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Nome del Progetto
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="es. Gestione Ordini Cliente"
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Descrizione o Obiettivo in Linguaggio Naturale
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Descrivi cosa deve contenere il tuo database (es. voglio gestire i clienti, i loro ordini e i prodotti acquistati...)"
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            />
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              Annulla
            </button>
            <button
              type="submit"
              className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-sm font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700"
            >
              {mode === 'wizard' ? 'Avvia Wizard Guidato →' : 'Crea Progetto Rapido'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
