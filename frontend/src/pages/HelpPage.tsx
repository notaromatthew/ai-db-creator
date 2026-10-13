import { Link } from 'react-router-dom'

const STEPS = [
  { icon: 'upload_file', title: 'Descrivi e carica', text: 'Crea un nuovo progetto dandogli un nome e, se vuoi, due righe su cosa deve gestire. Poi carica i tuoi documenti: PDF, testo, fogli di calcolo (XLSX, CSV) o script SQL. L\'IA legge sia il testo sia la struttura delle colonne.' },
  { icon: 'schema', title: 'Controlla lo schema', text: 'L\'IA propone tabelle, colonne e relazioni in forma normalizzata. Tu le guardi nel diagramma, correggi nomi e chiavi a mano oppure chiedi una modifica alla chat in linguaggio naturale. Nulla è definitivo finché non confermi.' },
  { icon: 'table_view', title: 'Popola i dati', text: 'Con "Popola dati" l\'IA estrae le righe dai tuoi documenti e le inserisce nelle tabelle rispettando le relazioni. Puoi esplorare, correggere e interrogare i dati scrivendo domande come "totale vendite per cliente".' },
  { icon: 'download', title: 'Esporta o condividi', text: 'Scarica lo script SQL (SQLite, PostgreSQL, MySQL o SQL Server) oppure condividi il progetto con colleghi e clienti, con il ruolo che decidi tu.' },
]

const ROLES = [
  { role: 'Proprietario', color: 'text-tecnia-primary', text: 'Può fare tutto: modificare, condividere, eliminare il progetto.' },
  { role: 'Editor', color: 'text-tecnia-magentaDeep', text: 'Carica documenti, modifica schema e dati. Non può condividere né eliminare.' },
  { role: 'Lettore', color: 'text-tecnia-muted', text: 'Vede schema e dati, fa domande in sola lettura ed esporta. Non cambia nulla.' },
]

export default function HelpPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 py-2">
      <header>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Guida in quattro passi</h1>
        <p className="mt-2 text-base text-tecnia-muted dark:text-slate-400">Dai tuoi documenti a un database pronto all'uso, senza scrivere codice.</p>
      </header>

      <ol className="flex flex-col gap-4">
        {STEPS.map((s, i) => (
          <li key={s.title} className="glass flex items-start gap-4 p-5">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#ff6b00] to-[#fe3ac6] font-headline font-bold text-white" aria-hidden="true">{i + 1}</span>
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold"><span className="material-symbols-outlined text-tecnia-primary" aria-hidden="true">{s.icon}</span>{s.title}</h2>
              <p className="mt-1 text-sm leading-6 text-tecnia-muted dark:text-slate-300">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <section aria-labelledby="share-help" className="glass p-6">
        <h2 id="share-help" className="text-xl font-bold">Condividere un progetto</h2>
        <p className="mt-2 text-sm leading-6 text-tecnia-muted dark:text-slate-300">
          Dal progetto, premi <strong>Condividi</strong>. Puoi invitare una persona con la sua email e scegliere se può leggere o modificare. Se non ha ancora un account, l'invito resta in attesa e si attiva quando si registra con quella email. Il progetto compare tra i <em>Condivisi con me</em>.
        </p>
        <p className="mt-2 text-sm leading-6 text-tecnia-muted dark:text-slate-300">
          Per chi non ha un account puoi creare un <strong>link pubblico in sola lettura</strong>: mostra nome e schema, non i documenti, e puoi revocarlo quando vuoi. Il link completo si vede una sola volta, appena lo crei.
        </p>
        <ul className="mt-4 divide-y divide-tecnia-line/40">
          {ROLES.map((r) => (
            <li key={r.role} className="flex flex-wrap items-center gap-3 py-3">
              <span className={`tag w-28 justify-center ${r.color}`}>{r.role}</span>
              <span className="min-w-[220px] flex-1 text-sm">{r.text}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-tecnia-muted dark:text-slate-400">Se un progetto condiviso non ti serve più, usa <strong>Lascia il progetto</strong> dalla tua pagina Progetti.</p>
      </section>

      <section aria-labelledby="privacy-help" className="glass p-6">
        <h2 id="privacy-help" className="text-xl font-bold">I tuoi dati restano tuoi</h2>
        <p className="mt-2 text-sm leading-6 text-tecnia-muted dark:text-slate-300">
          I progetti sono privati: li vedi solo tu e chi decidi di invitare. Chi amministra il servizio vede utenti e consumi, non il contenuto dei tuoi progetti.
        </p>
      </section>

      <div className="glass flex flex-wrap items-center justify-between gap-4 p-6">
        <div>
          <h2 className="font-bold">Pronto a cominciare?</h2>
          <p className="text-sm text-tecnia-muted dark:text-slate-400">Crea il tuo primo progetto: bastano un nome e qualche documento.</p>
        </div>
        <Link to="/app" className="primary-button">Vai ai progetti</Link>
      </div>
    </div>
  )
}
