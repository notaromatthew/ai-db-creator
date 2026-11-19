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
  { h: 'Di cosa si tratta', t: 'Stiamo studiando quanto aiuta uno strumento con intelligenza artificiale a progettare un database a partire da documenti. Ti chiediamo di svolgere un compito di circa 15 minuti.' },
  { h: 'Quali dati raccogliamo', t: 'La tua fascia di età, il tuo ruolo e due livelli di esperienza; i tempi e le azioni principali che compi nel compito; lo schema che costruisci. Non raccogliamo nome, email né indirizzo IP, e i dati non sono collegati al tuo account.' },
  { h: 'Come li usiamo', t: 'Solo in forma aggregata per la ricerca. Ti assegniamo a caso a uno di tre modi di lavorare: senza intelligenza artificiale, con la sola intelligenza artificiale o con l\'intelligenza artificiale e l\'interfaccia completa.' },
  { h: 'I tuoi diritti', t: 'Partecipare è volontario. Puoi ritirarti in qualsiasi momento, anche alla fine: i tuoi dati vengono cancellati. Ti daremo un codice personale: se vorrai la cancellazione più tardi, comunicalo a chi conduce lo studio.' },
]

export const TASK_BRIEF = 'Una piccola biblioteca di quartiere vuole tenere traccia di libri, autori, soci e prestiti. Progetta lo schema del database (tabelle, colonne, chiavi primarie e relazioni) e, se lo strumento lo permette, carica alcuni dati di esempio.'

export const ARM_TASK: Record<string, { title: string; text: string }> = {
  manual: { title: 'Lavora senza intelligenza artificiale', text: 'Disegna lo schema con l\'editor qui sotto. Non usare strumenti di intelligenza artificiale né schemi già pronti.' },
  ai_only: { title: 'Lavora con l\'assistente', text: 'Apri l\'app e descrivi l\'archivio all\'assistente: lascia che sia lui a proporre lo schema. Non modificare lo schema a mano.' },
  ai_interface: { title: 'Lavora con l\'assistente e l\'interfaccia', text: 'Apri l\'app, fatti proporre uno schema dall\'assistente e correggilo con il diagramma, la chat e le altre funzioni a tua disposizione.' },
}
