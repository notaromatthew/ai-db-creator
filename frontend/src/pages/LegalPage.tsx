// Pagine legali: i testi definitivi li fornisce TecnIA. Qui c'e' solo cio' che e' gia' vero,
// senza inventare clausole, e un segnaposto onesto per il resto.
const CONTENT = {
  privacy: {
    title: 'Informativa sulla privacy',
    intro: 'Come TecnIA tratta i tuoi dati quando usi AI-DB-Creator.',
    facts: [
      'Titolare del servizio: TecnIA di Davide Ditolve, P.IVA 04941440168, Arcene (BG).',
      'Per domande sui tuoi dati scrivi a info@tecniaweb.it.',
      'I progetti sono privati: li vedi solo tu e chi decidi di invitare. Chi amministra il servizio vede utenti e consumi, non il contenuto dei tuoi progetti.',
    ],
    todo: 'Il testo completo dell\'informativa (finalità, basi giuridiche, tempi di conservazione, fornitori coinvolti, diritti e modalità per esercitarli) è da fornire da TecnIA e non è ancora stato pubblicato.',
  },
  cookie: {
    title: 'Informativa sui cookie',
    intro: 'Quali cookie e dati salvati nel browser usa AI-DB-Creator.',
    facts: [
      'Il sito usa solo ciò che serve a farlo funzionare: la sessione di accesso (gestita da Keycloak) e alcune preferenze salvate nel tuo browser, come il tema chiaro o scuro e l\'aver già visto la presentazione iniziale.',
      'Non risultano cookie di pubblicità o di profilazione. Questo punto va confermato da TecnIA prima della pubblicazione.',
    ],
    todo: 'L\'elenco completo dei cookie e il testo definitivo dell\'informativa sono da fornire da TecnIA e non sono ancora stati pubblicati.',
  },
} as const

export default function LegalPage({ kind }: { kind: keyof typeof CONTENT }) {
  const c = CONTENT[kind]
  return (
    <article className="glass mx-auto max-w-3xl p-6 sm:p-8" aria-labelledby="legal-title">
      <h1 id="legal-title" className="text-3xl font-bold tracking-tight">{c.title}</h1>
      <p className="mt-2 text-tecnia-muted">{c.intro}</p>
      <ul className="mt-5 list-disc space-y-2 pl-5 text-sm leading-6">
        {c.facts.map((f) => <li key={f}>{f}</li>)}
      </ul>
      <p role="note" className="mt-6 flex items-start gap-3 rounded-xl border border-orange-300 bg-orange-50 p-4 text-sm text-tecnia-primary dark:border-orange-900 dark:bg-orange-950/30">
        <span className="material-symbols-outlined" aria-hidden="true">edit_note</span>
        <span><b>Testo da completare.</b> {c.todo}</span>
      </p>
    </article>
  )
}
