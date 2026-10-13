export const CONSENT_VERSION = '1.0'

export const AGE_BANDS = ['18-24', '25-34', '35-44', '45-54', '55+']
export const ROLES = [
  { value: 'studente', label: 'Studente o studentessa' },
  { value: 'sviluppatore', label: 'Sviluppo software' },
  { value: 'analista', label: 'Analisi dati o database' },
  { value: 'docente', label: 'Docente o ricercatore' },
  { value: 'altro', label: 'Altro' },
]

export const INFORMATIVA = [
  { h: 'Di cosa si tratta', t: 'Stiamo studiando quanto aiuta uno strumento con intelligenza artificiale a progettare un database a partire da documenti. Ti chiediamo di svolgere un compito di circa 15 minuti e di rispondere a due brevi questionari.' },
  { h: 'Quali dati raccogliamo', t: 'La tua fascia di età, il tuo ruolo e due livelli di esperienza; i tempi e le azioni principali che compi nel compito; lo schema che costruisci; le risposte ai questionari. Non raccogliamo nome, email né indirizzo IP, e le tue risposte non sono collegate al tuo account.' },
  { h: 'Come li usiamo', t: 'Solo in forma aggregata per la ricerca. Ti assegniamo a caso a uno di tre modi di lavorare: senza intelligenza artificiale, con la sola intelligenza artificiale o con l\'intelligenza artificiale e l\'interfaccia completa.' },
  { h: 'I tuoi diritti', t: 'Partecipare è volontario. Puoi ritirarti in qualsiasi momento, anche alla fine: i tuoi dati vengono cancellati. Ti daremo un codice personale: se vorrai la cancellazione più tardi, comunicalo a chi conduce lo studio.' },
]

export const TASK_BRIEF = 'Una piccola biblioteca di quartiere vuole tenere traccia di libri, autori, soci e prestiti. Progetta lo schema del database (tabelle, colonne, chiavi primarie e relazioni) e, se lo strumento lo permette, carica alcuni dati di esempio.'

export const ARM_TASK: Record<string, { title: string; text: string }> = {
  manual: { title: 'Lavora senza intelligenza artificiale', text: 'Disegna lo schema con l\'editor qui sotto. Non usare strumenti di intelligenza artificiale né schemi già pronti.' },
  ai_only: { title: 'Lavora con l\'assistente', text: 'Apri l\'app e descrivi l\'archivio all\'assistente: lascia che sia lui a proporre lo schema. Non modificare lo schema a mano.' },
  ai_interface: { title: 'Lavora con l\'assistente e l\'interfaccia', text: 'Apri l\'app, fatti proporre uno schema dall\'assistente e correggilo con il diagramma, la chat e le altre funzioni a tua disposizione.' },
}

export const TLX = [
  { key: 'mental_demand', label: 'Impegno mentale', hint: 'Quanto è stato impegnativo pensare, ricordare, decidere?', low: 'Basso', high: 'Alto' },
  { key: 'physical_demand', label: 'Impegno fisico', hint: 'Quanta attività fisica (clic, scrittura) ti è servita?', low: 'Basso', high: 'Alto' },
  { key: 'temporal_demand', label: 'Pressione del tempo', hint: 'Quanto ti sei sentito di fretta?', low: 'Bassa', high: 'Alta' },
  { key: 'performance', label: 'Riuscita', hint: 'Quanto sei soddisfatto di come è andata?', low: 'Perfetta', high: 'Fallimentare' },
  { key: 'effort', label: 'Fatica', hint: 'Quanto hai dovuto impegnarti per ottenere il risultato?', low: 'Poca', high: 'Molta' },
  { key: 'frustration', label: 'Frustrazione', hint: 'Quanto ti sei sentito insicuro, irritato, stressato?', low: 'Poca', high: 'Molta' },
]

export const SUS = [
  'Penso che userei volentieri questo strumento con frequenza.',
  'Ho trovato lo strumento inutilmente complesso.',
  'Ho trovato lo strumento facile da usare.',
  'Penso che mi servirebbe l\'aiuto di una persona esperta per usarlo.',
  'Ho trovato le varie funzioni ben integrate tra loro.',
  'Ho trovato troppe incoerenze nello strumento.',
  'Penso che la maggior parte delle persone imparerebbe a usarlo in fretta.',
  'Ho trovato lo strumento molto macchinoso da usare.',
  'Mi sono sentito sicuro nell\'usare lo strumento.',
  'Ho dovuto imparare molte cose prima di riuscire a usarlo.',
]
