import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Survey from '@/components/Survey'

const TASKS = [
  { title: 'Compito 1 · Crea uno schema da un documento', text: 'Carica un documento e controlla lo schema proposto dall\'IA.' },
  { title: 'Compito 2 · Correggi una relazione sbagliata', text: 'Ti guidiamo con un progetto già pronto.' },
  { title: 'Compito 3 · Esporta i dati', text: 'Crea il database, popolalo ed esporta il risultato.' },
]

function Ico({ n, className = '' }: { n: string; className?: string }) {
  return <span aria-hidden="true" className={`material-symbols-outlined ${className}`}>{n}</span>
}

export default function StudyPage(_props: { lang?: 'it' | 'en' }) {
  const [params] = useSearchParams()
  const [read, setRead] = useState(false)
  const [withdraw, setWithdraw] = useState(false)
  const [done, setDone] = useState<boolean[]>([false, false, false])
  const consent = read && withdraw
  const current = done.indexOf(false)
  const doneCount = done.filter(Boolean).length
  const projectId = params.get('progetto') || 'studio'

  const complete = (i: number) => setDone((d) => d.map((v, k) => (k === i ? true : v)))

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <span className="tag text-tecnia-magentaDeep dark:text-pink-300">Modalità ricerca</span>
        <h1 className="mt-2.5 text-3xl font-bold tracking-tight sm:text-[34px]">Partecipa allo studio</h1>
        <p className="mt-1.5 max-w-xl text-base text-tecnia-muted dark:text-slate-300">Svolgi tre compiti brevi e dicci com'è andata. Servono circa 15 minuti e puoi fermarti quando vuoi.</p>
      </div>

      <section className="glass flex flex-col gap-3.5 p-6" aria-labelledby="consent-h">
        <h2 id="consent-h" className="text-lg font-semibold">Consenso</h2>
        <label className="flex cursor-pointer items-start gap-3 text-sm leading-normal">
          <input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} className="mt-0.5 h-[22px] w-[22px] shrink-0 accent-tecnia-magentaDeep" />
          <span>Ho letto l'informativa e accetto che tempi, esiti e voti siano usati in forma aggregata per la ricerca.</span>
        </label>
        <label className="flex cursor-pointer items-start gap-3 text-sm leading-normal">
          <input type="checkbox" checked={withdraw} onChange={(e) => setWithdraw(e.target.checked)} className="mt-0.5 h-[22px] w-[22px] shrink-0 accent-tecnia-magentaDeep" />
          <span>So che posso ritirare il consenso in qualsiasi momento dalle impostazioni.</span>
        </label>
        <div><a href="/app/help" className="text-sm text-tecnia-magentaDeep underline dark:text-pink-300">Leggi l'informativa completa</a></div>
        {!consent && <p className="text-sm text-tecnia-muted dark:text-slate-300">Spunta entrambe le caselle per vedere i compiti.</p>}
      </section>

      {consent && (
        <>
          <section className="flex flex-col gap-3" aria-labelledby="tasks-h">
            <h2 id="tasks-h" className="text-lg font-semibold">I tuoi compiti</h2>
            <div className="h-1.5 max-w-[260px] overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700" role="progressbar" aria-label="Avanzamento" aria-valuemin={0} aria-valuemax={3} aria-valuenow={doneCount}>
              <i className="block h-full bg-gradient-to-r from-tecnia-orange to-tecnia-magenta" style={{ width: `${(doneCount / 3) * 100}%` }} />
            </div>
            {TASKS.map((t, i) => {
              const isDone = done[i]
              const isCur = i === current
              return (
                <div key={t.title} className={`glass flex flex-wrap items-center gap-4 px-5 py-5 ${isCur ? '!border-tecnia-magenta' : ''}`}>
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-headline text-sm font-bold ${isDone ? 'bg-tecnia-ok text-white' : isCur ? 'bg-gradient-to-br from-tecnia-orange to-tecnia-magenta text-white' : 'bg-slate-200 text-tecnia-muted'}`}>
                    {isDone ? <Ico n="check" className="!text-lg" /> : i + 1}
                  </span>
                  <div className="min-w-[200px] flex-1">
                    <h3 className="text-base font-semibold">{t.title}</h3>
                    <p className="mt-0.5 text-[13px] text-tecnia-muted dark:text-slate-300">{isDone ? 'Completato.' : isCur ? t.text : `Si sblocca dopo il compito ${i}.`}</p>
                  </div>
                  {isDone && <span className="tag text-tecnia-ok">Fatto</span>}
                  {isCur && (
                    <div className="flex flex-wrap gap-2">
                      <a className="primary-button !border-tecnia-magenta !text-tecnia-magentaDeep" href="/app">Apri l'app <Ico n="arrow_forward" /></a>
                      <button type="button" className="secondary-button" onClick={() => complete(i)}>Ho finito</button>
                    </div>
                  )}
                  {!isDone && !isCur && <span className="tag text-tecnia-muted">Da fare</span>}
                </div>
              )
            })}
          </section>

          <section className="glass flex flex-wrap items-center gap-4 p-6">
            <Ico n="star" className="!text-[28px] text-tecnia-magentaDeep" />
            <div className="min-w-[220px] flex-1">
              <h2 className="text-base font-semibold">Alla fine: un giudizio da 1 a 5</h2>
              <p className="mt-0.5 text-sm text-tecnia-muted dark:text-slate-300">Quanto è stato utile lo schema e quanto sono convincenti i dati. Un commento è facoltativo.</p>
            </div>
          </section>

          <Survey projectId={projectId} />
        </>
      )}
    </div>
  )
}
