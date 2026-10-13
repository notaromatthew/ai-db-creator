import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/api/client'
import ManualSchemaEditor from './research/ManualSchemaEditor'
import {
  AGE_BANDS, ARM_TASK, CONSENT_VERSION, INFORMATIVA, ROLES, SUS, TASK_BRIEF, TLX,
} from './research/studyTexts'

type Stage = 'loading' | 'consent' | 'demo' | 'code' | 'task' | 'tlx' | 'sus' | 'debrief' | 'done' | 'withdrawn'
interface Session { id: string; code: string; arm: string }

const STORE = 'aidb.study.v1'
const readSession = (): Session | null => {
  try { const raw = sessionStorage.getItem(STORE); return raw ? JSON.parse(raw) : null } catch { return null }
}
const writeSession = (s: Session | null) => {
  try { if (s) sessionStorage.setItem(STORE, JSON.stringify(s)); else sessionStorage.removeItem(STORE) } catch { /* senza archivio il percorso funziona comunque */ }
}

function Ico({ n, className = '' }: { n: string; className?: string }) {
  return <span aria-hidden="true" className={`material-symbols-outlined ${className}`}>{n}</span>
}

const STEP_ORDER: Stage[] = ['task', 'tlx', 'sus', 'debrief', 'done']
const STEP_LABEL = ['Compito', 'Carico di lavoro', 'Usabilità', 'Conclusione']

export default function StudyPage(_props: { lang?: 'it' | 'en' }) {
  const [stage, setStage] = useState<Stage>('loading')
  const [session, setSession] = useState<Session | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [read, setRead] = useState(false)
  const [voluntary, setVoluntary] = useState(false)
  const [demo, setDemo] = useState({ age_band: '', role: '', db_experience: 0, ai_experience: 0 })
  const [saved, setSaved] = useState(false)
  const started = useRef(false)

  const call = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true); setError('')
    try { return await fn() } catch (e) { setError((e as Error).message); return undefined } finally { setBusy(false) }
  }, [])

  // Ripresa: se la scheda è ancora aperta, si torna al passo in cui eri.
  useEffect(() => {
    const stored = readSession()
    if (!stored) { setStage('consent'); return }
    api.post(`/study/participants/${stored.id}/state`, { code: stored.code })
      .then((s: { step: Stage }) => { setSession(stored); setStage(s.step) })
      .catch(() => { writeSession(null); setStage('consent') })
  }, [])

  const event = useCallback((type: string, data: Record<string, unknown> = {}) => {
    if (!session) return
    api.post(`/study/participants/${session.id}/events`, { code: session.code, type, data }).catch(() => {})
  }, [session])

  useEffect(() => {
    if (stage === 'task' && session && !started.current) { started.current = true; event('task_start', { arm: session.arm }) }
  }, [stage, session, event])

  const enroll = async () => {
    const r = await call(() => api.post('/study/participants', { consent: true, consent_version: CONSENT_VERSION, demographics: demo }))
    if (!r) return
    const s = { id: r.participant_id, code: r.code, arm: r.arm }
    writeSession(s); setSession(s); setStage('code')
  }

  const post = async (path: string, body: Record<string, unknown>, next: Stage) => {
    if (!session) return
    const r = await call(() => api.post(`/study/participants/${session.id}/${path}`, { code: session.code, ...body }))
    if (r) setStage(next)
  }

  const saveSchema = async (tables: unknown[]) => {
    if (!session) return
    setSaved(false)
    const r = await call(() => api.put(`/study/participants/${session.id}/schema`, { code: session.code, tables }))
    if (r) setSaved(true)
  }

  const withdraw = async () => {
    if (!session) return
    if (!window.confirm('Vuoi ritirarti? I tuoi dati vengono cancellati e non potrai riprendere.')) return
    const r = await call(() => api.post(`/study/participants/${session.id}/withdraw`, { code: session.code }))
    if (r) { writeSession(null); setStage('withdrawn') }
  }

  const demoOk = !!demo.age_band && !!demo.role && demo.db_experience > 0 && demo.ai_experience > 0
  const stepIndex = STEP_ORDER.indexOf(stage)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <span className="tag text-tecnia-magentaDeep dark:text-pink-300">Modalità ricerca</span>
        <h1 className="mt-2.5 text-3xl font-bold tracking-tight sm:text-[34px]">Partecipa allo studio</h1>
        <p className="mt-1.5 max-w-xl text-base text-tecnia-muted dark:text-slate-300">Un compito di circa 15 minuti e due brevi questionari. Puoi fermarti quando vuoi.</p>
      </div>

      {stepIndex >= 0 && stage !== 'done' && (
        <ol className="flex flex-wrap gap-2 text-xs" aria-label="Avanzamento">
          {STEP_LABEL.map((l, i) => (
            <li key={l} aria-current={i === stepIndex ? 'step' : undefined} className={`rounded-full px-3 py-1 font-semibold ${i === stepIndex ? 'bg-orange-50 text-tecnia-primary dark:bg-slate-800' : i < stepIndex ? 'text-tecnia-ok' : 'text-tecnia-muted'}`}>{i + 1}. {l}</li>
          ))}
        </ol>
      )}

      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{error}</p>}

      {stage === 'loading' && <p role="status" className="text-sm text-tecnia-muted">Un momento…</p>}

      {stage === 'consent' && (
        <section className="glass flex flex-col gap-4 p-6" aria-labelledby="inf-h">
          <h2 id="inf-h" className="text-lg font-semibold">Informativa e consenso</h2>
          {INFORMATIVA.map((b) => (<div key={b.h}><h3 className="text-sm font-semibold">{b.h}</h3><p className="text-sm text-tecnia-muted dark:text-slate-300">{b.t}</p></div>))}
          <label className="flex cursor-pointer items-start gap-3 text-sm leading-normal">
            <input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} className="mt-0.5 h-[22px] w-[22px] shrink-0 accent-tecnia-magentaDeep" />
            <span>Ho letto l'informativa e accetto che i dati descritti siano usati in forma aggregata per la ricerca.</span>
          </label>
          <label className="flex cursor-pointer items-start gap-3 text-sm leading-normal">
            <input type="checkbox" checked={voluntary} onChange={(e) => setVoluntary(e.target.checked)} className="mt-0.5 h-[22px] w-[22px] shrink-0 accent-tecnia-magentaDeep" />
            <span>So che partecipare è volontario e che posso ritirarmi in ogni momento facendo cancellare i miei dati.</span>
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="primary-button" disabled={!(read && voluntary)} onClick={() => setStage('demo')}>Continua <Ico n="arrow_forward" /></button>
            {!(read && voluntary) && <span className="text-sm text-tecnia-muted">Spunta entrambe le caselle per continuare.</span>}
          </div>
        </section>
      )}

      {stage === 'demo' && (
        <section className="glass flex flex-col gap-4 p-6" aria-labelledby="demo-h">
          <h2 id="demo-h" className="text-lg font-semibold">Qualche domanda su di te</h2>
          <p className="text-sm text-tecnia-muted dark:text-slate-300">Servono solo a descrivere il gruppo di partecipanti. Non chiediamo nome né email.</p>
          <label className="flex flex-col gap-1 text-sm font-semibold">La tua fascia di età
            <select className="rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 font-normal dark:bg-slate-900" value={demo.age_band} onChange={(e) => setDemo({ ...demo, age_band: e.target.value })}>
              <option value="">Scegli…</option>{AGE_BANDS.map((a) => <option key={a}>{a}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-semibold">Il tuo ruolo
            <select className="rounded-xl border border-tecnia-line bg-white/80 px-3 py-2 font-normal dark:bg-slate-900" value={demo.role} onChange={(e) => setDemo({ ...demo, role: e.target.value })}>
              <option value="">Scegli…</option>{ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </label>
          {([['db_experience', 'La tua esperienza con i database'], ['ai_experience', 'La tua esperienza con strumenti di intelligenza artificiale']] as const).map(([key, label]) => (
            <fieldset key={key} className="flex flex-col gap-1.5">
              <legend className="text-sm font-semibold">{label} <span className="font-normal text-tecnia-muted">(1 = nessuna, 5 = molta)</span></legend>
              <div className="flex gap-4">
                {[1, 2, 3, 4, 5].map((n) => (
                  <label key={n} className="flex items-center gap-1.5 text-sm"><input type="radio" name={key} value={n} checked={demo[key] === n} onChange={() => setDemo({ ...demo, [key]: n })} />{n}</label>
                ))}
              </div>
            </fieldset>
          ))}
          <div className="flex gap-3">
            <button type="button" className="secondary-button" onClick={() => setStage('consent')}>Indietro</button>
            <button type="button" className="primary-button" disabled={!demoOk || busy} onClick={enroll}>Inizia lo studio</button>
          </div>
        </section>
      )}

      {stage === 'code' && session && (
        <section className="glass flex flex-col gap-3 p-6" aria-labelledby="code-h">
          <h2 id="code-h" className="text-lg font-semibold">Il tuo codice personale</h2>
          <p className="text-sm text-tecnia-muted dark:text-slate-300">Annotalo: lo vedi solo ora. Se vorrai far cancellare i tuoi dati dopo lo studio, comunicalo a chi lo conduce.</p>
          <p className="select-all rounded-xl bg-orange-50 p-4 text-center font-mono text-2xl font-bold tracking-widest dark:bg-slate-800" aria-label="Codice di ritiro">{session.code}</p>
          <div><button type="button" className="primary-button" onClick={() => setStage('task')}>Ho annotato il codice <Ico n="arrow_forward" /></button></div>
        </section>
      )}

      {stage === 'task' && session && (
        <section className="glass flex flex-col gap-4 p-6" aria-labelledby="task-h">
          <h2 id="task-h" className="text-lg font-semibold">Il tuo compito</h2>
          <p className="text-sm">{TASK_BRIEF}</p>
          <div className="rounded-xl bg-orange-50 p-4 dark:bg-slate-800">
            <h3 className="text-sm font-semibold">{ARM_TASK[session.arm]?.title}</h3>
            <p className="mt-1 text-sm">{ARM_TASK[session.arm]?.text}</p>
          </div>
          {session.arm === 'manual' ? (
            <ManualSchemaEditor onSave={saveSchema} saving={busy} saved={saved} error="" />
          ) : (
            <div><a href="/app" target="_blank" rel="noreferrer" className="primary-button" onClick={() => event('page_view', { page: 'app' })}>Apri l'app in una nuova scheda <Ico n="open_in_new" /></a></div>
          )}
          <div className="flex flex-wrap items-center gap-3 border-t border-tecnia-line/50 pt-4">
            <button type="button" className="primary-button" disabled={busy || (session.arm === 'manual' && !saved)} onClick={() => post('task/complete', {}, 'tlx')}>Ho finito il compito</button>
            {session.arm === 'manual' && !saved && <span className="text-xs text-tecnia-muted">Salva lo schema prima di concludere.</span>}
            <button type="button" className="secondary-button" onClick={() => event('help_request', { category: 'ambiente' })}>Segnala un problema tecnico</button>
          </div>
        </section>
      )}

      {stage === 'tlx' && <TlxForm busy={busy} onSubmit={(scores) => post('nasa-tlx', scores, 'sus')} />}
      {stage === 'sus' && <SusForm busy={busy} onSubmit={(scores) => post('sus', { scores }, 'debrief')} />}

      {stage === 'debrief' && (
        <DebriefForm busy={busy} onSubmit={(comment) => post('debrief', { comment }, 'done')} />
      )}

      {stage === 'done' && (
        <section className="glass flex flex-col gap-2 p-6" role="status">
          <Ico n="check_circle" className="!text-[32px] text-tecnia-ok" />
          <h2 className="text-lg font-semibold">Grazie, hai finito</h2>
          <p className="text-sm text-tecnia-muted dark:text-slate-300">Le tue risposte sono salvate in forma anonima. Se cambi idea, comunica il tuo codice a chi conduce lo studio e i tuoi dati verranno cancellati.</p>
        </section>
      )}

      {stage === 'withdrawn' && (
        <section className="glass flex flex-col gap-2 p-6" role="status">
          <h2 className="text-lg font-semibold">Ti sei ritirato</h2>
          <p className="text-sm text-tecnia-muted dark:text-slate-300">Abbiamo cancellato i tuoi dati. Grazie lo stesso per il tempo che ci hai dedicato.</p>
        </section>
      )}

      {session && ['task', 'tlx', 'sus', 'debrief'].includes(stage) && (
        <p className="text-sm"><button type="button" className="text-tecnia-magentaDeep underline dark:text-pink-300" onClick={withdraw}>Ritira la mia partecipazione e cancella i miei dati</button></p>
      )}
    </div>
  )
}

function TlxForm({ busy, onSubmit }: { busy: boolean; onSubmit: (scores: Record<string, number>) => void }) {
  const [scores, setScores] = useState<Record<string, number>>({})
  const complete = TLX.every((q) => scores[q.key] !== undefined)
  return (
    <form className="glass flex flex-col gap-5 p-6" aria-labelledby="tlx-h" onSubmit={(e) => { e.preventDefault(); if (complete) onSubmit(scores) }}>
      <h2 id="tlx-h" className="text-lg font-semibold">Com'è andato il compito? (NASA-TLX)</h2>
      <p className="text-sm text-tecnia-muted dark:text-slate-300">Per ogni voce sposta il cursore: da 0 a 100.</p>
      {TLX.map((q) => (
        <div key={q.key} className="flex flex-col gap-1">
          <label htmlFor={`tlx-${q.key}`} className="text-sm font-semibold">{q.label} <span className="font-normal text-tecnia-muted">· {q.hint}</span></label>
          <input id={`tlx-${q.key}`} type="range" min={0} max={100} step={5} value={scores[q.key] ?? 50}
            onChange={(e) => setScores({ ...scores, [q.key]: Number(e.target.value) })}
            onPointerDown={() => scores[q.key] === undefined && setScores((s) => ({ ...s, [q.key]: 50 }))}
            onKeyDown={() => scores[q.key] === undefined && setScores((s) => ({ ...s, [q.key]: 50 }))}
            aria-valuetext={scores[q.key] === undefined ? 'non ancora scelto' : String(scores[q.key])} />
          <div className="flex justify-between text-xs text-tecnia-muted"><span>{q.low}</span><span>{scores[q.key] === undefined ? 'scegli un valore' : scores[q.key]}</span><span>{q.high}</span></div>
        </div>
      ))}
      <div><button type="submit" className="primary-button" disabled={!complete || busy}>Continua</button></div>
    </form>
  )
}

function SusForm({ busy, onSubmit }: { busy: boolean; onSubmit: (scores: number[]) => void }) {
  const [scores, setScores] = useState<(number | undefined)[]>(Array(SUS.length).fill(undefined))
  const complete = scores.every((s) => s !== undefined)
  return (
    <form className="glass flex flex-col gap-5 p-6" aria-labelledby="sus-h" onSubmit={(e) => { e.preventDefault(); if (complete) onSubmit(scores as number[]) }}>
      <h2 id="sus-h" className="text-lg font-semibold">Quanto è stato facile da usare? (SUS)</h2>
      <p className="text-sm text-tecnia-muted dark:text-slate-300">1 = per niente d'accordo, 5 = del tutto d'accordo.</p>
      {SUS.map((q, i) => (
        <fieldset key={q} className="flex flex-col gap-1.5">
          <legend className="text-sm">{i + 1}. {q}</legend>
          <div className="flex gap-4">
            {[1, 2, 3, 4, 5].map((n) => (
              <label key={n} className="flex items-center gap-1.5 text-sm"><input type="radio" name={`sus-${i}`} checked={scores[i] === n} onChange={() => setScores(scores.map((s, k) => (k === i ? n : s)))} aria-label={`Domanda ${i + 1}, risposta ${n}`} />{n}</label>
            ))}
          </div>
        </fieldset>
      ))}
      <div><button type="submit" className="primary-button" disabled={!complete || busy}>Continua</button></div>
    </form>
  )
}

function DebriefForm({ busy, onSubmit }: { busy: boolean; onSubmit: (comment: string) => void }) {
  const [comment, setComment] = useState('')
  return (
    <form className="glass flex flex-col gap-4 p-6" aria-labelledby="deb-h" onSubmit={(e) => { e.preventDefault(); onSubmit(comment) }}>
      <h2 id="deb-h" className="text-lg font-semibold">Un'ultima cosa</h2>
      <p className="text-sm text-tecnia-muted dark:text-slate-300">Lo studio confronta tre modi di progettare un database: senza intelligenza artificiale, con la sola intelligenza artificiale e con l'intelligenza artificiale più l'interfaccia completa. Ti avevamo assegnato a uno di questi a caso per poterli confrontare in modo equo. Non c'erano risposte giuste o sbagliate: ci interessa come ti sei trovato.</p>
      <label className="flex flex-col gap-1 text-sm font-semibold">Vuoi aggiungere un commento? (facoltativo)
        <textarea className="min-h-24 rounded-xl border border-tecnia-line bg-white/80 p-3 text-sm font-normal dark:bg-slate-900" value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} />
      </label>
      <p className="text-xs text-tecnia-muted">Non scrivere dati personali: se compaiono email o indirizzi, li oscuriamo.</p>
      <div><button type="submit" className="primary-button" disabled={busy}>Concludi lo studio</button></div>
    </form>
  )
}
