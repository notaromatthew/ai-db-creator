export type Lang = 'it' | 'en'

export interface Copy {
  title: string
  description: string
  skip: string
  nav: { how: string; research: string; examples: string; help: string; login: string; register: string; langLabel: string }
  hero: {
    eyebrow: string; titleA: string; titleB: string; text: string
    cta: string; cta2: string; note: string
    previewLabel: string; previewTitle: string; previewCount: string
    table: string; key: string; unique: string; example: string
  }
  steps: { eyebrow: string; title: string; items: { icon: string; title: string; text: string }[] }
  research: {
    eyebrow: string; title: string; text: string; cta: string; ctaStudy: string
    items: { icon: string; title: string; text: string }[]
  }
  faq: { eyebrow: string; title: string; items: { q: string; a: string }[] }
  final: { titleA: string; titleB: string; titleC: string; login: string; register: string }
}

export const copy: Record<Lang, Copy> = {
  it: {
    title: 'AI-DB-Creator · Dai tuoi documenti a un database',
    description: 'Carichi i documenti, l\'IA propone lo schema, tu lo controlli. Poi crei un database PostgreSQL vero e lo popoli con dati coerenti. Un progetto di ricerca TecnIA.',
    skip: 'Vai al contenuto',
    nav: { how: 'Come funziona', research: 'Ricerca', examples: 'Esempi', help: 'Guida', login: 'Accedi', register: 'Registrati', langLabel: 'Lingua' },
    hero: {
      eyebrow: 'Progetto di ricerca · TecnIA',
      titleA: 'Dai tuoi documenti a un database ',
      titleB: 'pronto da usare',
      text: 'Carichi i file, l\'IA propone lo schema, tu lo controlli e lo correggi. Poi genera i dati e li esporta. Ogni passaggio resta visibile e modificabile.',
      cta: 'Provalo ora', cta2: 'Crea un account',
      note: 'Gratuito per chi partecipa allo studio. Accesso con email.',
      previewLabel: 'Anteprima dello schema generato', previewTitle: 'Schema proposto', previewCount: '3 tabelle',
      table: 'tabella', key: 'chiave', unique: 'unico',
      example: 'Esempio illustrativo. Nell\'app lo schema nasce dai tuoi documenti.',
    },
    steps: {
      eyebrow: 'Come funziona', title: 'Quattro passi, nessun comando',
      items: [
        { icon: 'upload_file', title: '1 · Carica', text: 'PDF, testo o fogli di calcolo. Anche pochi file bastano per iniziare.' },
        { icon: 'schema', title: '2 · Controlla lo schema', text: 'L\'IA propone tabelle e relazioni. Tu le approvi o le modifichi.' },
        { icon: 'database', title: '3 · Crea il database', text: 'Con un clic ottieni un database PostgreSQL vero, già strutturato.' },
        { icon: 'table_chart', title: '4 · Popola ed esporta', text: 'Dati coerenti con lo schema, esportabili in SQL o CSV.' },
      ],
    },
    research: {
      eyebrow: 'Perché è anche una ricerca',
      title: 'Misuriamo quanto l\'IA sbaglia, e lo diciamo',
      text: 'AI-DB-Creator nasce per studiare quanto bene i modelli linguistici costruiscono schemi e dati. Nell\'app trovi i benchmark, i metodi e le versioni congelate dei risultati.',
      cta: 'Vedi i benchmark', ctaStudy: 'Partecipa allo studio',
      items: [
        { icon: 'fact_check', title: 'Risultati verificabili.', text: 'Ogni esecuzione registra modello, parametri e prompt.' },
        { icon: 'groups', title: 'Studio con utenti.', text: 'Puoi partecipare e dirci dove il tool ti ha convinto o no.' },
        { icon: 'menu_book', title: 'Metodo aperto.', text: 'Domande di ricerca e limiti sono scritti in chiaro.' },
      ],
    },
    faq: {
      eyebrow: 'Domande frequenti', title: 'Prima di iniziare',
      items: [
        { q: 'Serve saper programmare?', a: 'No. Lavori con schemi e tabelle, senza scrivere comandi. Se conosci SQL puoi comunque modificare tutto.' },
        { q: 'Che cosa succede ai miei documenti?', a: 'Servono solo a costruire il tuo progetto. Puoi cancellarli in qualsiasi momento insieme al progetto.' },
        { q: 'Quanto costa?', a: 'Per chi partecipa allo studio è gratuito. L\'accesso avviene con la tua email.' },
        { q: 'Posso fidarmi dello schema proposto?', a: 'Può contenere errori: per questo lo controlli tu prima di creare il database.' },
      ],
    },
    final: { titleA: 'Pronto a provarlo sui ', titleB: 'tuoi', titleC: ' documenti?', login: 'Accedi all\'app', register: 'Registrati' },
  },
  en: {
    title: 'AI-DB-Creator · From your documents to a database',
    description: 'Upload your documents, the AI proposes a schema, you review it. Then create a real PostgreSQL database and fill it with consistent data. A TecnIA research project.',
    skip: 'Skip to content',
    nav: { how: 'How it works', research: 'Research', examples: 'Examples', help: 'Help', login: 'Log in', register: 'Sign up', langLabel: 'Language' },
    hero: {
      eyebrow: 'Research project · TecnIA',
      titleA: 'From your documents to a database ',
      titleB: 'ready to use',
      text: 'Upload your files and the AI proposes a schema. You review and fix it, then it generates the data and exports it. Every step stays visible and editable.',
      cta: 'Try it now', cta2: 'Create an account',
      note: 'Free for study participants. Sign in with your email.',
      previewLabel: 'Preview of the generated schema', previewTitle: 'Proposed schema', previewCount: '3 tables',
      table: 'table', key: 'key', unique: 'unique',
      example: 'Illustrative example. In the app, the schema comes from your own documents.',
    },
    steps: {
      eyebrow: 'How it works', title: 'Four steps, no commands',
      items: [
        { icon: 'upload_file', title: '1 · Upload', text: 'PDFs, text or spreadsheets. A few files are enough to start.' },
        { icon: 'schema', title: '2 · Review the schema', text: 'The AI proposes tables and relations. You approve or edit them.' },
        { icon: 'database', title: '3 · Create the database', text: 'One click gives you a real PostgreSQL database, already structured.' },
        { icon: 'table_chart', title: '4 · Fill and export', text: 'Data consistent with the schema, exportable as SQL or CSV.' },
      ],
    },
    research: {
      eyebrow: 'Why it is also research',
      title: 'We measure how often the AI gets it wrong, and we say so',
      text: 'AI-DB-Creator exists to study how well language models build schemas and data. In the app you will find the benchmarks, the methods and frozen versions of the results.',
      cta: 'See the benchmarks', ctaStudy: 'Join the study',
      items: [
        { icon: 'fact_check', title: 'Verifiable results.', text: 'Every run records the model, its parameters and the prompt.' },
        { icon: 'groups', title: 'A study with users.', text: 'You can take part and tell us where the tool convinced you, or not.' },
        { icon: 'menu_book', title: 'Open method.', text: 'Research questions and limits are written in plain view.' },
      ],
    },
    faq: {
      eyebrow: 'FAQ', title: 'Before you start',
      items: [
        { q: 'Do I need to know how to code?', a: 'No. You work with schemas and tables, without typing commands. If you know SQL you can still edit everything.' },
        { q: 'What happens to my documents?', a: 'They are only used to build your project. You can delete them at any time along with the project.' },
        { q: 'How much does it cost?', a: 'It is free for study participants. You sign in with your email.' },
        { q: 'Can I trust the proposed schema?', a: 'It may contain mistakes, which is why you review it before creating the database.' },
      ],
    },
    final: { titleA: 'Ready to try it on ', titleB: 'your', titleC: ' documents?', login: 'Open the app', register: 'Sign up' },
  },
}
