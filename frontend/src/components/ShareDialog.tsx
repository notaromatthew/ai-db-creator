import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useDialog } from '@/hooks/useDialog'
import { useDraft } from '@/hooks/useDraft'

interface Person { id?: string; user_id?: string; email: string | null; name: string | null; role?: string }
interface Invite { id: string; email: string; role: string; expires_at: string }
interface LinkRow { id: string; expires_at: string }
interface Sharing { owner: Person; members: (Person & { user_id: string })[]; invites: Invite[]; links: LinkRow[] }

const ROLES = [
  { value: 'viewer', label: 'Può leggere' },
  { value: 'editor', label: 'Può modificare' },
]

const initials = (p: { name?: string | null; email?: string | null }) => {
  const base = (p.name || p.email || '?').trim()
  const parts = base.split(/[\s@.]+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '?') + (parts[1]?.[0] ?? '')).toUpperCase()
}
const fmtDate = (iso: string) => new Date(iso.endsWith('Z') ? iso : iso + 'Z').toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })
const errText = (e: any, fallback: string) => (e && typeof e.message === 'string' && e.message ? e.message : fallback)

export default function ShareDialog({ projectId, open, onClose }: { projectId: string; open: boolean; onClose: () => void }) {
  const ref = useDialog<HTMLDivElement>(open, onClose)
  const [data, setData] = useState<Sharing | null>(null)
  const [loadError, setLoadError] = useState('')
  // email e ruolo in compilazione si salvano in sessione: se la sessione scade non si perdono
  const [email, setEmail] = useDraft(`share.email.${projectId}`, '')
  const [role, setRole] = useDraft(`share.role.${projectId}`, 'editor')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    try {
      setData(await api.get(`/projects/${projectId}/sharing`))
      setLoadError('')
    } catch (e: any) {
      setLoadError(errText(e, 'Non riusciamo a caricare la condivisione. Solo il proprietario può gestirla: se lo sei, chiudi e riapri la finestra.'))
    }
  }, [projectId])

  useEffect(() => {
    if (open) { setMessage(''); setError(''); setNewUrl(''); setCopied(false); load() }
  }, [open, load])

  if (!open) return null

  const run = async (action: () => Promise<any>, ok?: string) => {
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await action()
      if (ok) setMessage(ok)
      await load()
      return result
    } catch (e: any) {
      setError(errText(e, 'Operazione non riuscita. Controlla la connessione e riprova.'))
    } finally {
      setBusy(false)
    }
  }

  const invite = async (event: React.FormEvent) => {
    event.preventDefault()
    const value = email.trim()
    if (!value) return
    const result = await run(() => api.post(`/projects/${projectId}/invites`, { email: value, role }))
    if (result) {
      setEmail('')
      setMessage(result.status === 'member'
        ? `${result.email} ha già un account: ora trova il progetto tra i condivisi.`
        : `Invito creato per ${result.email}: si attiva appena si registra con questa email.`)
    }
  }

  const createLink = async () => {
    const result = await run(() => api.post(`/projects/${projectId}/links`, {}))
    if (result?.path) { setNewUrl(window.location.origin + result.path); setCopied(false) }
  }

  const copy = async () => {
    try { await navigator.clipboard.writeText(newUrl); setCopied(true) } catch { setError('Non riesco a copiare: selezionalo e copialo a mano.') }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-tecnia-ink/45 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="share-title" className="my-auto flex w-full max-w-[620px] flex-col gap-5 rounded-3xl border border-tecnia-line/50 bg-white/95 p-6 shadow-[0_20px_60px_rgba(26,34,51,.3)] sm:p-7 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="share-title" className="text-2xl font-bold tracking-tight">Condividi il progetto</h2>
            <p className="mt-1 text-sm text-tecnia-muted dark:text-slate-400">Chi inviti lo trova tra i progetti condivisi con lui.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Chiudi" className="rounded-full p-1 text-tecnia-muted hover:bg-orange-50 dark:hover:bg-slate-800"><span className="material-symbols-outlined">close</span></button>
        </div>

        {loadError ? (
          <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{loadError}</p>
        ) : !data ? (
          <p role="status" className="text-sm text-tecnia-muted">Sto caricando…</p>
        ) : (
          <>
            <form onSubmit={invite}>
              <label htmlFor="share-email" className="mb-2 block font-headline text-[13px] font-semibold">Invita con l'email</label>
              <div className="flex flex-wrap gap-2.5">
                <input id="share-email" data-autofocus type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@esempio.it" className="field min-w-0 flex-1" />
                <select aria-label="Ruolo dell'invitato" value={role} onChange={(e) => setRole(e.target.value)} className="field !w-auto font-headline font-semibold">
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <button type="submit" disabled={busy || !email.trim()} className="primary-button">Invita</button>
              </div>
              <p className="mt-2 text-xs text-tecnia-muted dark:text-slate-400">Se la persona non ha un account, l'invito resta in attesa finché non si registra con questa email.</p>
            </form>

            <div aria-live="polite">
              {message && <p role="status" className="rounded-xl bg-green-50 px-3 py-2 text-sm font-medium text-tecnia-ok dark:bg-green-950/40">{message}</p>}
              {error && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
            </div>

            <div>
              <span className="mb-1 block font-headline text-[13px] font-semibold">Chi ha accesso</span>
              <ul className="divide-y divide-tecnia-line/40">
                <li className="flex items-center gap-3 py-3">
                  <span className="avatar">{initials(data.owner)}</span>
                  <div className="min-w-0 flex-1"><b className="block truncate font-headline text-sm">{data.owner.name || data.owner.email}</b><span className="block truncate text-xs text-tecnia-muted">{data.owner.email}</span></div>
                  <span className="tag text-tecnia-primary">Proprietario</span>
                </li>
                {data.members.map((m) => (
                  <li key={m.user_id} className="flex flex-wrap items-center gap-3 py-3" data-testid="member-row">
                    <span className="avatar">{initials(m)}</span>
                    <div className="min-w-0 flex-1"><b className="block truncate font-headline text-sm">{m.name || m.email}</b><span className="block truncate text-xs text-tecnia-muted">{m.email}</span></div>
                    <select aria-label={`Ruolo di ${m.name || m.email}`} value={m.role} disabled={busy} onChange={(e) => run(() => api.put(`/projects/${projectId}/members/${m.user_id}`, { role: e.target.value }))} className="field !w-auto !py-2 font-headline text-sm font-semibold">
                      {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                    <button type="button" disabled={busy} onClick={() => run(() => api.delete(`/projects/${projectId}/members/${m.user_id}`))} className="rounded-full px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/40" aria-label={`Rimuovi ${m.name || m.email}`}>Rimuovi</button>
                  </li>
                ))}
                {data.invites.map((i) => (
                  <li key={i.id} className="flex flex-wrap items-center gap-3 py-3">
                    <span className="avatar !bg-slate-500 !bg-none">{initials({ email: i.email })}</span>
                    <div className="min-w-0 flex-1"><b className="block truncate font-headline text-sm">{i.email}</b><span className="block text-xs text-tecnia-muted">Invito in attesa · {ROLES.find((r) => r.value === i.role)?.label.toLowerCase()} · scade il {fmtDate(i.expires_at)}</span></div>
                    <span className="tag text-amber-700">In attesa</span>
                    <button type="button" disabled={busy} onClick={() => run(() => api.delete(`/projects/${projectId}/invites/${i.id}`))} className="rounded-full px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/40" aria-label={`Annulla l'invito a ${i.email}`}>Annulla</button>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-col gap-3 border-t border-tecnia-line pt-4">
              <span className="font-headline text-[13px] font-semibold">Link pubblico in sola lettura</span>
              <p className="text-[13px] text-tecnia-muted dark:text-slate-400">Chiunque abbia il link vede nome e schema del progetto, ma non i documenti caricati e non può modificare nulla. Il link vale 30 giorni.</p>
              {newUrl && (
                <div className="rounded-xl border border-orange-200 bg-orange-50/60 p-3">
                  <p className="mb-2 text-xs font-semibold text-tecnia-primary">Copialo adesso: per sicurezza non lo mostriamo più.</p>
                  <div className="flex flex-wrap gap-2.5">
                    <input readOnly value={newUrl} aria-label="Link pubblico" onFocus={(e) => e.currentTarget.select()} className="field min-w-0 flex-1 font-mono text-xs" />
                    <button type="button" onClick={copy} className="secondary-button"><span className="material-symbols-outlined">content_copy</span>{copied ? 'Copiato' : 'Copia'}</button>
                  </div>
                </div>
              )}
              {data.links.length > 0 && (
                <ul className="divide-y divide-tecnia-line/40">
                  {data.links.map((l) => (
                    <li key={l.id} className="flex items-center gap-3 py-2.5">
                      <span className="material-symbols-outlined text-tecnia-primary">link</span>
                      <span className="flex-1 text-sm">Link attivo · scade il {fmtDate(l.expires_at)}</span>
                      <button type="button" disabled={busy} onClick={() => { setNewUrl(''); run(() => api.delete(`/projects/${projectId}/links/${l.id}`), 'Link revocato: smette di funzionare subito.') }} className="secondary-button !border-red-700 !text-red-700">Revoca</button>
                    </li>
                  ))}
                </ul>
              )}
              <div><button type="button" onClick={createLink} disabled={busy} className="secondary-button">Crea un link pubblico</button></div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
