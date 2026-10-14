import { useEffect } from 'react'
import { LogoMark } from '@/brand/Logo'
import SiteFooter from '@/brand/SiteFooter'
import { useConfig } from '@/config/AppConfig'
import { copy, type Lang } from './copy'

const grad = 'bg-gradient-to-r from-tecnia-orange to-tecnia-magenta bg-clip-text text-transparent'
const eyebrow = 'font-headline text-xs font-bold uppercase tracking-[.08em] text-tecnia-primary dark:text-orange-300'
const muted = 'text-tecnia-muted dark:text-slate-300'
const bigBtn = 'px-8 py-4 text-[13px]'

function Ico({ n, className = '' }: { n: string; className?: string }) {
  return <span aria-hidden="true" className={`material-symbols-outlined ${className}`}>{n}</span>
}

function Row({ a, b, k, mute }: { a: string; b?: string; k?: boolean; mute?: string }) {
  return (
    <div className="flex justify-between gap-2 border-b border-tecnia-line/40 px-3 py-1.5 last:border-0">
      <span>{k && <span className="font-bold text-tecnia-magentaDeep">id</span>}{k ? ' · ' : ''}{a}{b ? ` · ${b}` : ''}</span>
      <span className={muted}>{mute}</span>
    </div>
  )
}

function Table({ name, label, children }: { name: string; label: string; children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border border-tecnia-line bg-white text-xs text-tecnia-ink dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
      <div className="flex justify-between border-b border-tecnia-line bg-slate-100 px-3 py-2 font-headline font-bold dark:border-slate-700 dark:bg-slate-800">
        <span>{name}</span><span className={`font-normal ${muted}`}>{label}</span>
      </div>
      {children}
    </div>
  )
}

export function Hero({ lang }: { lang: Lang }) {
  const t = copy[lang].hero
  return (
    <section className="relative z-10 mx-auto max-w-[1160px] px-4 pb-16 pt-10 sm:px-8 sm:pb-24 sm:pt-16">
      <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_.9fr]">
        <div className="flex flex-col gap-6">
          <span className={eyebrow}>{t.eyebrow}</span>
          <h1 className="text-4xl font-bold leading-[1.05] tracking-tight [text-wrap:balance] sm:text-6xl">{t.titleA}<span className={grad}>{t.titleB}</span></h1>
          <p className={`max-w-[540px] text-lg leading-relaxed sm:text-[19px] ${muted}`}>{t.text}</p>
          <div className="flex flex-wrap gap-3.5 pt-2">
            <a className={`primary-button ${bigBtn}`} href="/app">{t.cta} <Ico n="arrow_forward" /></a>
            <a className={`secondary-button ${bigBtn} !border-tecnia-magenta !text-tecnia-magentaDeep dark:!text-pink-300`} href="/app?register=1">{t.cta2}</a>
          </div>
          <p className={`text-[13px] ${muted}`}>{t.note}</p>
        </div>
        <div className="glass flex flex-col gap-3 p-5" role="img" aria-label={t.previewLabel}>
          <div className="flex items-center justify-between">
            <span className="font-headline text-sm font-semibold">{t.previewTitle}</span>
            <span className={`${eyebrow} !text-[11px]`}>{t.previewCount}</span>
          </div>
          <Table name="clienti" label={t.table}>
            <Row k a="intero" mute={t.key} /><Row a="ragione_sociale" b={lang === 'it' ? 'testo' : 'text'} /><Row a="partita_iva" b={lang === 'it' ? 'testo' : 'text'} mute={t.unique} />
          </Table>
          <Table name="ordini" label={t.table}>
            <Row k a="intero" mute={t.key} /><Row a="cliente_id" b={lang === 'it' ? 'intero' : 'integer'} mute="→ clienti.id" /><Row a="importo" b={lang === 'it' ? 'decimale' : 'decimal'} />
          </Table>
          <p className={`text-xs ${muted}`}>{t.example}</p>
        </div>
      </div>
    </section>
  )
}

export function Steps({ lang }: { lang: Lang }) {
  const t = copy[lang].steps
  return (
    <section id="come" aria-labelledby="steps-h" className="relative z-10 mx-auto max-w-[1160px] scroll-mt-20 px-4 pb-16 sm:px-8 sm:pb-24">
      <div className="mb-9 flex flex-col gap-3"><span className={eyebrow}>{t.eyebrow}</span><h2 id="steps-h" className="text-3xl font-bold tracking-tight sm:text-[40px]">{t.title}</h2></div>
      <ol className="grid list-none gap-5 p-0 sm:grid-cols-2 lg:grid-cols-4">
        {t.items.map((s) => (
          <li key={s.title} className="glass flex flex-col gap-3 !rounded-3xl p-6">
            <Ico n={s.icon} className="!text-[30px] text-tecnia-primary dark:text-orange-300" />
            <h3 className="text-xl font-semibold">{s.title}</h3>
            <p className={`text-[15px] leading-normal ${muted}`}>{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

export function Research({ lang }: { lang: Lang }) {
  const t = copy[lang].research
  const { config } = useConfig()
  const rm = config.research_mode
  return (
    <section id="ricerca" aria-labelledby="res-h" className="relative z-10 mx-auto max-w-[1160px] scroll-mt-20 px-4 pb-16 sm:px-8 sm:pb-24">
      <div className="glass grid items-center gap-10 !rounded-3xl p-6 sm:p-12 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <span className={eyebrow}>{t.eyebrow}</span>
          <h2 id="res-h" className="text-3xl font-bold tracking-tight sm:text-4xl">{t.title}</h2>
          <p className={`text-base leading-relaxed ${muted}`}>{t.text}</p>
          {rm && (
            <div className="flex flex-wrap gap-3">
              <a className="secondary-button !border-tecnia-magenta !text-tecnia-magentaDeep dark:!text-pink-300" href={`/app/benchmark`}>{t.cta} <Ico n="arrow_forward" /></a>
              <a className="secondary-button" href="/app/studio">{t.ctaStudy}</a>
            </div>
          )}
        </div>
        <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
          {t.items.map((i) => (
            <li key={i.icon} className="flex items-start gap-3.5">
              <Ico n={i.icon} className="text-tecnia-magentaDeep dark:text-pink-300" />
              <p className="text-[15px] leading-normal"><b>{i.title}</b> {i.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export function Faq({ lang }: { lang: Lang }) {
  const t = copy[lang].faq
  return (
    <section id="faq" aria-labelledby="faq-h" className="relative z-10 mx-auto max-w-[860px] scroll-mt-20 px-4 pb-16 sm:px-8 sm:pb-24">
      <div className="mb-8 flex flex-col gap-3"><span className={eyebrow}>{t.eyebrow}</span><h2 id="faq-h" className="text-3xl font-bold tracking-tight sm:text-4xl">{t.title}</h2></div>
      <div className="flex flex-col gap-3">
        {t.items.map((f) => (
          <details key={f.q} className="glass group px-5 py-4">
            <summary className="flex min-h-6 cursor-pointer list-none items-center justify-between gap-4 font-headline font-semibold">
              {f.q}<Ico n="expand_more" className="transition group-open:rotate-180" />
            </summary>
            <p className={`mt-3 text-[15px] leading-relaxed ${muted}`}>{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

export default function Landing({ lang = 'it' }: { lang?: Lang }) {
  const c = copy[lang]
  const { config } = useConfig()
  const home = lang === 'it' ? '/' : '/en/'

  useEffect(() => {
    const prevTitle = document.title
    const prevLang = document.documentElement.lang
    document.title = c.title
    document.documentElement.lang = lang
    let meta = document.querySelector('meta[name="description"]') as HTMLMetaElement | null
    const created = !meta
    if (!meta) { meta = document.createElement('meta'); meta.name = 'description'; document.head.appendChild(meta) }
    const prevDesc = meta.content
    meta.content = c.description
    return () => {
      document.title = prevTitle
      document.documentElement.lang = prevLang
      if (created) meta?.remove(); else if (meta) meta.content = prevDesc
    }
  }, [lang, c.title, c.description])

  const navLink = 'rounded-full px-3 py-3 font-headline text-sm font-semibold hover:text-tecnia-primary dark:hover:text-orange-300'
  const langLink = (code: Lang, href: string) => (
    <a href={href} hrefLang={code} lang={code} aria-current={lang === code ? 'true' : undefined}
      className={`${navLink} !px-2 ${lang === code ? 'text-tecnia-primary underline underline-offset-4 dark:text-orange-300' : ''}`}>{code.toUpperCase()}</a>
  )

  return (
    <div className="relative min-h-screen overflow-hidden bg-tecnia-bg text-tecnia-ink dark:bg-slate-950 dark:text-slate-100">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-3 focus:text-tecnia-ink">{c.skip}</a>
      <div aria-hidden="true" className="orb -left-40 -top-44 h-[560px] w-[560px]" style={{ background: 'radial-gradient(circle,#ff6b00,transparent 70%)' }} />
      <div aria-hidden="true" className="orb -right-52 top-[620px] h-[560px] w-[560px]" style={{ background: 'radial-gradient(circle,#fe3ac6,transparent 70%)' }} />

      <header className="sticky top-0 z-30 border-b border-tecnia-line/30 bg-tecnia-bg/80 backdrop-blur-md dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-[1160px] flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 py-2 sm:px-8">
          <a href={home} className="inline-flex items-center gap-2.5 py-2 font-headline text-lg font-bold tracking-tight sm:text-xl">
            <LogoMark size={30} />
            <span>AI-DB-Creator <span className={`hidden text-[13px] font-normal sm:inline ${muted}`}>· by TecnIA</span></span>
          </a>
          <nav aria-label="Principale" className="flex flex-wrap items-center gap-x-1">
            <a className={`${navLink} hidden sm:inline-block`} href="#come">{c.nav.how}</a>
            <a className={`${navLink} hidden sm:inline-block`} href="#ricerca">{c.nav.research}</a>
            <a className={navLink} href="/app/examples">{c.nav.examples}</a>
            <a className={navLink} href="/app/help">{c.nav.help}</a>
            <span role="group" aria-label={c.nav.langLabel} className="flex">{langLink('it', '/')}{langLink('en', '/en/')}</span>
            <a className="primary-button ml-1" href="/app">{c.nav.login}</a>
            {config.registration_open && <a className="secondary-button hidden !border-tecnia-magenta !text-tecnia-magentaDeep sm:inline-flex dark:!text-pink-300" href="/app?register=1">{c.nav.register}</a>}
          </nav>
        </div>
      </header>

      <main id="main">
        <Hero lang={lang} />
        <Steps lang={lang} />
        <Research lang={lang} />
        <Faq lang={lang} />
        <section aria-labelledby="final-h" className="relative z-10 mx-auto flex max-w-[1160px] flex-col items-center gap-5 px-4 pb-16 text-center sm:px-8">
          <h2 id="final-h" className="text-3xl font-bold tracking-tight sm:text-[40px]">{c.final.titleA}<span className={grad}>{c.final.titleB}</span>{c.final.titleC}</h2>
          <div className="flex flex-wrap justify-center gap-3.5">
            <a className={`primary-button ${bigBtn}`} href="/app">{c.final.login}</a>
            <a className={`secondary-button ${bigBtn} !border-tecnia-magenta !text-tecnia-magentaDeep dark:!text-pink-300`} href="/app?register=1">{c.final.register}</a>
          </div>
        </section>
      </main>
      <SiteFooter lang={lang} />
    </div>
  )
}
