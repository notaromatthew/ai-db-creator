import { Link, useInRouterContext } from 'react-router-dom'

const linkCls = 'underline underline-offset-2 hover:text-tecnia-primary'

// Dentro il router i link interni non ricaricano la pagina; fuori (test isolati) restano link normali.
function InternalLink({ to, children }: { to: string; children: React.ReactNode }) {
  const inRouter = useInRouterContext()
  return inRouter ? <Link className={linkCls} to={to}>{children}</Link> : <a className={linkCls} href={to}>{children}</a>
}

// Dati TecnIA: devono comparire in fondo a ogni pagina.
export default function SiteFooter({ lang = 'it' }: { lang?: 'it' | 'en' }) {
  const it = lang === 'it'
  const year = new Date().getFullYear()
  return (
    <footer className="relative z-10 border-t border-tecnia-line bg-white/50 px-6 py-5 text-xs leading-relaxed text-tecnia-muted dark:bg-slate-950/50 sm:px-10" aria-label={it ? 'Informazioni su TecnIA' : 'About TecnIA'}>
      <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-x-8 gap-y-3">
        <div>
          <b className="font-headline text-[13px] text-tecnia-ink">TecnIA</b> · {it ? 'Intelligenza Artificiale su Misura' : 'Tailored Artificial Intelligence'}
          <br />
          © {year} TecnIA di Davide Ditolve. {it ? 'Tutti i diritti riservati.' : 'All rights reserved.'} · {it ? 'P.IVA' : 'VAT'} 04941440168 · Arcene (BG) 24040
        </div>
        <div className="sm:text-right">
          info@tecniaweb.it · <a className={linkCls} href="https://tecniaweb.it">tecniaweb.it</a>
          <br />
          <InternalLink to="/app/privacy">Privacy</InternalLink> · <a className={linkCls} href="mailto:info@tecniaweb.it">{it ? 'Contatti' : 'Contact'}</a> · <InternalLink to="/app/cookie">Cookie</InternalLink>
        </div>
      </div>
    </footer>
  )
}
