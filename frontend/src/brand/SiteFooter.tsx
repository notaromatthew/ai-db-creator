// Dati TecnIA: devono comparire in fondo a ogni pagina.
export default function SiteFooter({ lang = 'it' }: { lang?: 'it' | 'en' }) {
  const it = lang === 'it'
  return (
    <footer className="relative z-10 border-t border-tecnia-line bg-white/50 px-6 py-5 text-xs leading-relaxed text-tecnia-muted dark:border-slate-800 dark:bg-slate-950/50 dark:text-slate-400 sm:px-10">
      <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-x-8 gap-y-3">
        <div>
          <b className="font-headline text-[13px] text-tecnia-ink dark:text-white">TecnIA</b> · {it ? 'Intelligenza Artificiale su Misura' : 'Tailored Artificial Intelligence'}
          <br />
          © 2026 TecnIA di Davide Ditolve. {it ? 'Tutti i diritti riservati.' : 'All rights reserved.'} · {it ? 'P.IVA' : 'VAT'} 04941440168 · Arcene (BG) 24040
        </div>
        <div className="sm:text-right">
          info@tecniaweb.it · <a className="underline" href="https://tecniaweb.it">tecniaweb.it</a>
          <br />
          <a className="underline" href="https://tecniaweb.it/privacy">Privacy</a> · <a className="underline" href="https://tecniaweb.it/contatti">{it ? 'Contatti' : 'Contact'}</a> · Cookie
        </div>
      </div>
    </footer>
  )
}
