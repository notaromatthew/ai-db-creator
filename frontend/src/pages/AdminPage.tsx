import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

interface Overview { users: number; projects: number; ai_calls_today: number; daily_budget: number; research_mode: boolean; llm_provider: string }
interface AdminUser { id: string; email: string | null; name: string | null; blocked: boolean; projects: number; ai_calls_total: number; daily_quota: number; custom_quota: boolean; last_seen_at: string | null }
interface Settings { default_daily_ai_quota: number; daily_ai_budget_total: number; max_upload_mb: number; max_projects_per_user: number; registration_open: boolean; maintenance_message: string; ai_enabled?: boolean }
type FormSettings = Omit<Settings, 'ai_enabled'>
interface LinkItem { id: string; project_id: string; project_name: string | null; created_by: string | null; expires_at: string }
interface UsageCount { key: string; count: number }
interface AuditRow { actor: string | null; action: string; target: string | null; detail: Record<string, unknown> | null; at: string }

const TABS = [
  { id: 'settings', label: 'Impostazioni' },
  { id: 'users', label: 'Utenti' },
  { id: 'usage', label: 'Uso e costi' },
  { id: 'links', label: 'Link pubblici' },
  { id: 'audit', label: 'Registro modifiche' },
] as const
type TabId = typeof TABS[number]['id']

const KIND_LABEL: Record<string, string> = { generate: 'Generazione schema', populate: 'Popolamento dati', chat: 'Chat sullo schema', query: 'Domande ai dati' }
const ACTION_LABEL: Record<string, string> = { 'user.update': 'Modifica utente', 'settings.update': 'Modifica impostazioni' }
const SETTING_LABEL: Record<string, string> = {
  default_daily_ai_quota: 'Quota giornaliera', daily_ai_budget_total: 'Tetto giornaliero', max_upload_mb: 'Limite upload',
  max_projects_per_user: 'Progetti per utente', registration_open: 'Registrazione', maintenance_message: 'Avviso', ai_enabled: 'Chiamate AI attive',
}

const fmtDateTime = (iso: string) => new Date(iso.endsWith('Z') ? iso : iso + 'Z').toLocaleString('it-IT', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const fmtValue = (v: unknown) => (v === true ? 'sì' : v === false ? 'no' : v === '' ? 'nessuno' : String(v))
const errText = (e: any, fallback: string) => (e && typeof e.message === 'string' && e.message ? e.message : fallback)

function Row({ title, hint, children, htmlFor }: { title: string; hint: string; children: React.ReactNode; htmlFor?: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-tecnia-line/40 py-4 last:border-b-0">
      <div className="min-w-0">
        {htmlFor ? <label htmlFor={htmlFor} className="block font-headline text-[15px] font-bold">{title}</label> : <b className="block font-headline text-[15px]">{title}</b>}
        <span className="text-[13px] text-tecnia-muted dark:text-slate-400">{hint}</span>
      </div>
      {children}
    </div>
  )
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
      className={`relative h-[26px] w-[46px] flex-none rounded-full transition ${checked ? 'bg-gradient-to-r from-[#ff6b00] to-[#fe3ac6]' : 'bg-slate-300 dark:bg-slate-600'}`}>
      <span className={`absolute top-[3px] h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? 'left-[23px]' : 'left-[3px]'}`} />
    </button>
  )
}

function SettingsTab({ overview }: { overview?: Overview }) {
  const queryClient = useQueryClient()
  const { data } = useQuery<Settings>({ queryKey: ['admin', 'settings'], queryFn: () => api.get('/admin/settings') })
  const [form, setForm] = useState<FormSettings | null>(null)
  const [aiBusy, setAiBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => { if (data) { const { ai_enabled: _ai, ...rest } = data; setForm(rest) } }, [data])
  if (!form || !data) return <p role="status" className="text-tecnia-muted">Sto caricando le impostazioni…</p>

  const set = <K extends keyof FormSettings>(k: K, v: FormSettings[K]) => setForm({ ...form, [k]: v })
  const num = (k: keyof FormSettings) => (e: React.ChangeEvent<HTMLInputElement>) => set(k, (e.target.value === '' ? 0 : Math.max(0, parseInt(e.target.value, 10) || 0)) as never)

  const save = async () => {
    setErr(''); setMsg('')
    const changed = Object.fromEntries((Object.keys(form) as (keyof FormSettings)[]).filter((k) => form[k] !== data[k]).map((k) => [k, form[k]]))
    if (!Object.keys(changed).length) { setMsg('Non c\'è nulla da salvare.'); return }
    try {
      await api.put('/admin/settings', changed)
      setMsg('Modifiche salvate. Valgono subito per tutti.')
      queryClient.invalidateQueries({ queryKey: ['admin'] })
    } catch (e: any) { setErr(errText(e, 'Non siamo riusciti a salvare. Riprova.')) }
  }

  const aiEnabled = data.ai_enabled !== false
  const toggleAi = async (next: boolean) => {
    const question = next
      ? 'Riattivare le chiamate AI per tutti gli utenti?'
      : 'Spegnere le chiamate AI per tutti gli utenti? Generazione, chat e popolamento si fermano subito, finché non le riattivi.'
    if (!window.confirm(question)) return
    setErr(''); setMsg(''); setAiBusy(true)
    try {
      await api.put('/admin/settings', { ai_enabled: next })
      setMsg(next ? 'Chiamate AI riattivate per tutti.' : 'Chiamate AI spente per tutti.')
      queryClient.invalidateQueries({ queryKey: ['admin'] })
    } catch (e: any) { setErr(errText(e, 'Non siamo riusciti a cambiare l\'interruttore. Riprova.')) }
    finally { setAiBusy(false) }
  }

  const numCls = '!w-28 text-right'
  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <section className="glass px-6 py-2" aria-labelledby="mod-title">
        <h2 id="mod-title" className="pb-1 pt-4 text-lg font-bold">Modificabili ora</h2>
        <Row title="Chiamate AI attive" hint={aiEnabled ? 'Interruttore generale: se lo spegni, nessuno può usare l\'IA finché non lo riaccendi.' : 'Le chiamate AI sono spente per tutti. Gli utenti vedono un avviso.'}>
          <span className={aiBusy ? 'opacity-50' : ''}><Toggle checked={aiEnabled} onChange={toggleAi} label="Chiamate AI attive" /></span>
        </Row>
        <Row title="Registrazione aperta" hint="Chiudila se serve fermare nuovi iscritti."><Toggle checked={form.registration_open} onChange={(v) => set('registration_open', v)} label="Registrazione aperta" /></Row>
        <Row title="Chiamate AI al giorno per utente" hint="Superata la quota l'utente vede un messaggio chiaro." htmlFor="s-quota"><input id="s-quota" type="number" min={0} className={`field ${numCls}`} value={form.default_daily_ai_quota} onChange={num('default_daily_ai_quota')} /></Row>
        <Row title="Tetto di chiamate AI giornaliero" hint="Raggiunto il tetto, le chiamate AI si fermano fino a domani." htmlFor="s-budget"><input id="s-budget" type="number" min={0} className={`field ${numCls}`} value={form.daily_ai_budget_total} onChange={num('daily_ai_budget_total')} /></Row>
        <Row title="Dimensione massima di un file" hint="In megabyte, per ogni documento caricato." htmlFor="s-upload"><input id="s-upload" type="number" min={0} className={`field ${numCls}`} value={form.max_upload_mb} onChange={num('max_upload_mb')} /></Row>
        <Row title="Progetti per utente" hint="Oltre il limite non si possono creare nuovi progetti." htmlFor="s-projects"><input id="s-projects" type="number" min={0} className={`field ${numCls}`} value={form.max_projects_per_user} onChange={num('max_projects_per_user')} /></Row>
        <Row title="Messaggio di manutenzione" hint="Mostrato in alto in tutta l'app. Vuoto = nessun avviso." htmlFor="s-msg"><input id="s-msg" type="text" maxLength={300} className="field !w-64" placeholder="Nessun avviso" value={form.maintenance_message} onChange={(e) => set('maintenance_message', e.target.value)} /></Row>
        <div className="flex flex-wrap items-center gap-4 pb-4 pt-4">
          <button type="button" onClick={save} className="primary-button">Salva le modifiche</button>
          <span aria-live="polite" className="text-sm">{msg && <span className="font-medium text-tecnia-ok">{msg}</span>}{err && <span role="alert" className="font-medium text-red-700 dark:text-red-300">{err}</span>}</span>
        </div>
      </section>
      <aside className="glass px-6 py-2 self-start" aria-labelledby="cool-title">
        <h2 id="cool-title" className="pb-1 pt-4 text-lg font-bold">Si cambiano da Coolify</h2>
        <Row title="Modalità ricerca" hint="Cambia con un redeploy."><span className={`tag ${overview?.research_mode ? 'text-tecnia-ok' : 'text-tecnia-muted'}`}>{overview?.research_mode ? 'Accesa' : 'Spenta'}</span></Row>
        <Row title="Fornitore del modello" hint="Configurato lato server."><code className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs dark:bg-slate-800">{overview?.llm_provider ?? '—'}</code></Row>
      </aside>
    </div>
  )
}

function UsersTab() {
  const queryClient = useQueryClient()
  const { data: users, isLoading } = useQuery<AdminUser[]>({ queryKey: ['admin', 'users'], queryFn: () => api.get('/admin/users') })
  const [quota, setQuota] = useState<Record<string, string>>({})
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  const update = async (id: string, body: Record<string, unknown>, ok: string) => {
    setErr(''); setMsg('')
    try {
      await api.put(`/admin/users/${id}`, body)
      setMsg(ok)
      setQuota((q) => { const { [id]: _drop, ...rest } = q; return rest })
      queryClient.invalidateQueries({ queryKey: ['admin'] })
    } catch (e: any) { setErr(errText(e, 'Operazione non riuscita.')) }
  }

  if (isLoading) return <p role="status" className="text-tecnia-muted">Sto caricando gli utenti…</p>
  return (
    <section className="glass py-2" aria-labelledby="users-title">
      <div className="px-5 pb-2 pt-4"><h2 id="users-title" className="text-lg font-bold">Utenti</h2>
        <div aria-live="polite" className="min-h-5 text-sm">{msg && <span className="font-medium text-tecnia-ok">{msg}</span>}{err && <span role="alert" className="font-medium text-red-700 dark:text-red-300">{err}</span>}</div></div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wide text-tecnia-muted">
            <th className="px-5 py-2 font-semibold">Utente</th><th className="px-2 py-2 font-semibold">Progetti</th><th className="px-2 py-2 font-semibold">Chiamate AI</th>
            <th className="px-2 py-2 font-semibold">Quota al giorno</th><th className="px-2 py-2 font-semibold">Ultimo accesso</th><th className="px-5 py-2 text-right font-semibold">Azioni</th></tr></thead>
          <tbody>
            {(users ?? []).map((u) => {
              const label = u.name || u.email || u.id
              const draft = quota[u.id]
              return (
                <tr key={u.id} className="border-t border-tecnia-line/40 align-middle">
                  <td className="px-5 py-3"><b className="block font-headline">{label}</b><span className="text-xs text-tecnia-muted">{u.email}</span>{u.blocked && <span className="tag ml-2 text-red-700 dark:text-red-300">Sospeso</span>}</td>
                  <td className="px-2 py-3">{u.projects}</td>
                  <td className="px-2 py-3">{u.ai_calls_total}</td>
                  <td className="px-2 py-3">
                    <div className="flex items-center gap-2">
                      <input type="number" min={0} aria-label={`Quota giornaliera di ${label}`} className="field !w-20 !py-1.5 text-right" value={draft ?? String(u.daily_quota)} onChange={(e) => setQuota({ ...quota, [u.id]: e.target.value })} />
                      {draft !== undefined && draft !== String(u.daily_quota) && draft !== '' && (
                        <button type="button" className="secondary-button !min-h-9 !px-3" onClick={() => update(u.id, { daily_quota: parseInt(draft, 10) }, `Quota di ${label} aggiornata.`)}>Salva</button>
                      )}
                      {u.custom_quota && draft === undefined && <span className="tag text-tecnia-magentaDeep">Personale</span>}
                    </div>
                  </td>
                  <td className="px-2 py-3 text-xs text-tecnia-muted">{u.last_seen_at ? fmtDateTime(u.last_seen_at) : 'mai'}</td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap justify-end gap-2">
                      {u.custom_quota && <button type="button" className="secondary-button !min-h-9 !px-3" onClick={() => update(u.id, { reset_quota: true }, `Quota di ${label} ripristinata al valore predefinito.`)} aria-label={`Ripristina la quota di ${label}`}>Ripristina quota</button>}
                      <button type="button" className={`secondary-button !min-h-9 !px-3 ${u.blocked ? '' : '!border-red-700 !text-red-700'}`} onClick={() => update(u.id, { blocked: !u.blocked }, u.blocked ? `${label} può di nuovo accedere.` : `${label} è stato sospeso.`)} aria-label={`${u.blocked ? 'Riattiva' : 'Sospendi'} ${label}`}>{u.blocked ? 'Riattiva' : 'Sospendi'}</button>
                    </div>
                  </td>
                </tr>
              )
            })}
            {!users?.length && <tr><td colSpan={6} className="px-5 py-8 text-center text-tecnia-muted">Nessun utente registrato.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function UsageList({ title, id, rows, label, loading, error }: { title: string; id: string; rows: UsageCount[]; label?: (key: string) => string; loading: boolean; error: unknown }) {
  return (
    <section className="glass self-start px-6 py-4" aria-labelledby={id}>
      <h2 id={id} className="text-lg font-bold">{title}</h2>
      {loading ? <p role="status" className="mt-3 text-tecnia-muted">Sto caricando i consumi…</p>
        : error ? <p role="alert" className="mt-3 font-medium text-red-700 dark:text-red-300">{errText(error, 'Non riusciamo a caricare questi consumi. Riprova tra poco.')}</p>
        : rows.length === 0 ? <p className="mt-3 text-tecnia-muted">Nessuna chiamata AI in questo periodo.</p>
        : <ul className="mt-3 divide-y divide-tecnia-line/40">
            {rows.map((r) => <li key={r.key} className="flex justify-between gap-3 py-2.5 text-sm"><span className="min-w-0 truncate">{label ? label(r.key) : r.key}</span><b className="font-headline">{r.count}</b></li>)}
          </ul>}
    </section>
  )
}

function UsageTab() {
  const [days, setDays] = useState(14)
  const q = (group: 'user' | 'day' | 'kind') => useQuery<UsageCount[]>({ queryKey: ['admin', 'usage', group, days], queryFn: () => api.get(`/admin/usage?group=${group}&days=${days}`) })
  const byDayQ = q('day'); const byKindQ = q('kind'); const byUserQ = q('user')
  const byDay = useMemo(() => [...(byDayQ.data ?? [])].sort((a, b) => b.key.localeCompare(a.key)), [byDayQ.data])
  const total = byDay.reduce((s, r) => s + r.count, 0)
  const max = Math.max(1, ...byDay.map((r) => r.count))
  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <section className="glass px-6 py-4" aria-labelledby="usage-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="usage-title" className="text-lg font-bold">Chiamate AI per giorno</h2>
          <div className="flex gap-2" role="group" aria-label="Periodo">
            {[7, 14, 30].map((n) => <button key={n} type="button" aria-pressed={days === n} onClick={() => setDays(n)} className={`rounded-full border px-3.5 py-1.5 font-headline text-[13px] font-semibold ${days === n ? 'border-orange-500 text-tecnia-primary' : 'border-tecnia-line'}`}>{n} giorni</button>)}
          </div>
        </div>
        <p className="mt-1 text-sm text-tecnia-muted">{total} chiamate negli ultimi {days} giorni.</p>
        {byDayQ.isLoading ? <p role="status" className="mt-4 text-tecnia-muted">Sto caricando i consumi…</p>
          : byDayQ.error ? <p role="alert" className="mt-4 font-medium text-red-700 dark:text-red-300">{errText(byDayQ.error, 'Non riusciamo a caricare i consumi. Riprova tra poco.')}</p>
          : byDay.length === 0 ? <p className="mt-4 text-tecnia-muted">Nessuna chiamata AI in questo periodo.</p>
          : (
          <ul className="mt-4 space-y-2">
            {byDay.map((r) => (
              <li key={r.key} className="flex items-center gap-3 text-sm">
                <span className="w-24 flex-none text-tecnia-muted">{new Date(r.key).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><i className="block h-full bg-gradient-to-r from-[#ff6b00] to-[#fe3ac6]" style={{ width: `${(r.count / max) * 100}%` }} /></span>
                <b className="w-10 text-right font-headline">{r.count}</b>
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="flex flex-col gap-6">
        <UsageList id="kind-title" title="Per tipo di operazione" rows={byKindQ.data ?? []} label={(k) => KIND_LABEL[k] ?? k} loading={byKindQ.isLoading} error={byKindQ.error} />
        <UsageList id="user-title" title="Per utente" rows={byUserQ.data ?? []} loading={byUserQ.isLoading} error={byUserQ.error} />
      </div>
    </div>
  )
}

function LinksTab() {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useQuery<LinkItem[]>({ queryKey: ['admin', 'links'], queryFn: () => api.get('/admin/links') })
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState<string | null>(null)

  const revoke = async (l: LinkItem) => {
    const name = l.project_name || l.project_id
    if (!window.confirm(`Revocare il link pubblico del progetto “${name}”? Smette di funzionare subito.`)) return
    setErr(''); setMsg(''); setBusy(l.id)
    try {
      await api.delete(`/admin/links/${l.id}`)
      setMsg(`Link di “${name}” revocato.`)
      queryClient.invalidateQueries({ queryKey: ['admin', 'links'] })
    } catch (e: any) { setErr(errText(e, 'Non siamo riusciti a revocare il link. Riprova.')) }
    finally { setBusy(null) }
  }

  return (
    <section className="glass px-6 py-2" aria-labelledby="links-title">
      <h2 id="links-title" className="pb-1 pt-4 text-lg font-bold">Link pubblici attivi</h2>
      <p className="text-sm text-tecnia-muted">Link in sola lettura creati dai proprietari dei progetti. Revocandone uno smette di funzionare subito.</p>
      <div aria-live="polite" className="min-h-5 pt-2 text-sm">{msg && <span className="font-medium text-tecnia-ok">{msg}</span>}{err && <span role="alert" className="font-medium text-red-700 dark:text-red-300">{err}</span>}</div>
      {isLoading ? <p role="status" className="py-6 text-tecnia-muted">Sto caricando i link…</p>
        : error ? <p role="alert" className="py-6 font-medium text-red-700 dark:text-red-300">{errText(error, 'Non riusciamo a caricare i link. Riprova tra poco.')}</p>
        : !data?.length ? <p className="py-6 text-tecnia-muted">Nessun link pubblico attivo.</p>
        : (
        <ul>
          {data.map((l) => (
            <li key={l.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-tecnia-line/40 py-3.5 last:border-b-0">
              <div className="min-w-0">
                <b className="block truncate font-headline text-[15px]">{l.project_name || l.project_id}</b>
                <span className="text-[13px] text-tecnia-muted">Creato da {l.created_by ?? 'sconosciuto'} · scade il {fmtDateTime(l.expires_at)}</span>
              </div>
              <button type="button" disabled={busy === l.id} onClick={() => revoke(l)} aria-label={`Revoca il link di ${l.project_name || l.project_id}`} className="secondary-button !min-h-9 !border-red-700 !px-4 !text-red-700 dark:!text-red-300">Revoca</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function AuditTab() {
  const { data, isLoading } = useQuery<AuditRow[]>({ queryKey: ['admin', 'audit'], queryFn: () => api.get('/admin/audit') })
  if (isLoading) return <p role="status" className="text-tecnia-muted">Sto caricando il registro…</p>
  return (
    <section className="glass px-6 py-2" aria-labelledby="audit-title">
      <h2 id="audit-title" className="pb-1 pt-4 text-lg font-bold">Ultime modifiche</h2>
      {!data?.length && <p className="py-6 text-tecnia-muted">Nessuna modifica registrata finora.</p>}
      <ul>
        {(data ?? []).map((r, i) => (
          <li key={i} className="flex flex-wrap items-center justify-between gap-3 border-b border-tecnia-line/40 py-3.5 last:border-b-0">
            <div className="min-w-0">
              <b className="block font-headline text-[15px]">{ACTION_LABEL[r.action] ?? r.action}</b>
              <span className="text-[13px] text-tecnia-muted">{r.actor ?? 'sistema'} · {fmtDateTime(r.at)}{r.target ? ` · utente ${r.target}` : ''}</span>
            </div>
            <span className="max-w-md text-right text-[13px] text-tecnia-muted">
              {Object.entries(r.detail ?? {}).map(([k, v]) => `${SETTING_LABEL[k] ?? (k === 'blocked' ? 'Sospeso' : k === 'daily_quota' ? 'Quota giornaliera' : k)}: ${fmtValue(v)}`).join(' · ')}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function AdminPage(_props: { lang?: 'it' | 'en' }) {
  const [tab, setTab] = useState<TabId>('settings')
  const { data: overview } = useQuery<Overview>({ queryKey: ['admin', 'overview'], queryFn: () => api.get('/admin/overview') })
  const kpis = [
    { label: 'Utenti', value: overview?.users, hint: 'account registrati' },
    { label: 'Progetti', value: overview?.projects, hint: 'in tutto il servizio' },
    { label: 'Chiamate AI oggi', value: overview ? `${overview.ai_calls_today} / ${overview.daily_budget}` : undefined, hint: 'sul tetto giornaliero' },
  ]
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Admin</h1>
        <p className="mt-1.5 text-base text-tecnia-muted dark:text-slate-400">Impostazioni, utenti e consumi. Chi è admin si decide su Keycloak.</p>
      </header>

      <div className="glass flex items-start gap-3 p-4 text-sm">
        <span className="material-symbols-outlined text-tecnia-magentaDeep">visibility_off</span>
        <p className="text-tecnia-muted dark:text-slate-300">Da qui vedi metadati e consumi, mai il contenuto dei progetti degli altri utenti: schemi, dati e documenti restano privati.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {kpis.map((k) => (
          <div key={k.label} className="glass flex flex-col gap-1 p-5">
            <span className="text-[13px] text-tecnia-muted">{k.label}</span>
            <b className="font-headline text-3xl">{k.value ?? '…'}</b>
            <span className="text-xs text-tecnia-muted">{k.hint}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2.5" role="tablist" aria-label="Sezioni admin">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls="admin-panel" onClick={() => setTab(t.id)}
            className={`min-h-10 rounded-full border bg-white px-4 font-headline text-[13px] font-semibold dark:bg-slate-800 ${tab === t.id ? 'border-orange-500 text-tecnia-primary' : 'border-tecnia-line'}`}>{t.label}</button>
        ))}
      </div>

      <div id="admin-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'settings' && <SettingsTab overview={overview} />}
        {tab === 'users' && <UsersTab />}
        {tab === 'usage' && <UsageTab />}
        {tab === 'links' && <LinksTab />}
        {tab === 'audit' && <AuditTab />}
      </div>
    </div>
  )
}
