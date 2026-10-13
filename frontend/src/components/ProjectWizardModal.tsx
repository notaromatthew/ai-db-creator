import React, { useState } from 'react'
import { useDialog } from '@/hooks/useDialog'

interface ProjectWizardModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateProject: (name: string, prompt: string, mode: 'quick' | 'wizard') => void
  busy?: boolean
  error?: string
}

/** Finestra "Nuovo progetto": un nome e, se vuoi, due righe su cosa deve contenere il database. */
export const ProjectWizardModal: React.FC<ProjectWizardModalProps> = ({ isOpen, onClose, onCreateProject, busy, error }) => {
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const ref = useDialog<HTMLDivElement>(isOpen, onClose)

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onCreateProject(name.trim(), prompt.trim(), 'wizard')
    setName('')
    setPrompt('')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-tecnia-ink/45 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="new-project-title" className="w-full max-w-lg rounded-3xl border border-tecnia-line/50 bg-white/95 p-7 shadow-[0_20px_60px_rgba(26,34,51,.3)] dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="new-project-title" className="text-2xl font-bold tracking-tight">Nuovo progetto</h2>
            <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">Bastano un nome e due righe: lo schema lo proponiamo noi.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Chiudi" className="rounded-full p-1 text-tecnia-muted hover:bg-orange-50"><span className="material-symbols-outlined">close</span></button>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label htmlFor="wiz-name" className="mb-2 block font-headline text-[13px] font-semibold">Nome del progetto</label>
            <input id="wiz-name" data-autofocus type="text" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Es. Ordini clienti" className="field" autoComplete="off" />
          </div>
          <div>
            <label htmlFor="wiz-prompt" className="mb-2 block font-headline text-[13px] font-semibold">Cosa deve gestire? <span className="font-normal text-tecnia-muted">(facoltativo)</span></label>
            <textarea id="wiz-prompt" rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Es. Clienti, ordini e prodotti. Ogni ordine ha più righe." className="field resize-y" />
          </div>
          {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700">{error}</p>}
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} className="secondary-button">Annulla</button>
            <button type="submit" disabled={!name.trim() || busy} className="primary-button">{busy ? 'Creazione in corso…' : 'Crea e continua'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
