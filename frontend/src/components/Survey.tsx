import { useState } from 'react'
import { api } from '@/api/client'

interface Props { projectId: string }

const NASA_TLX_QUESTIONS = [
  { key: 'mental_demand', label: 'Domanda mentale', low: 'Bassa', high: 'Alta' },
  { key: 'physical_demand', label: 'Domanda fisica', low: 'Bassa', high: 'Alta' },
  { key: 'temporal_demand', label: 'Pressione temporale', low: 'Bassa', high: 'Alta' },
  { key: 'performance', label: 'Prestazione', low: 'Perfetta', high: 'Fallimentare' },
  { key: 'effort', label: 'Sforzo', low: 'Basso', high: 'Alto' },
  { key: 'frustration', label: 'Frustrazione', low: 'Bassa', high: 'Alta' },
]

const SUS_QUESTIONS = [
  'Penso che userei frequentemente questo sistema',
  'Ho trovato il sistema inutilmente complesso',
  'Ho trovato il sistema facile da usare',
  'Penso che avrei bisogno del supporto di una persona tecnica per usare questo sistema',
  'Ho trovato le varie funzionalità del sistema ben integrate',
  'Ho trovato troppe incoerenze in questo sistema',
  'Penso che la maggior parte delle persone imparerebbe a usare questo sistema molto rapidamente',
  'Ho trovato il sistema molto macchinoso da usare',
  "Mi sono sentito molto sicuro nell'usare il sistema",
  'Ho dovuto imparare molte cose prima di riuscire a usare questo sistema',
]

export default function Survey({ projectId }: Props) {
  const [active, setActive] = useState<'nasa' | 'sus' | null>(null)
  const [nasaScores, setNasaScores] = useState<Record<string, number>>({})
  const [susScores, setSusScores] = useState<number[]>([])
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const nasaComplete = Object.keys(nasaScores).length === NASA_TLX_QUESTIONS.length
  const susComplete = susScores.filter((score) => score !== undefined).length === 10

  const submit = async (kind: 'nasa' | 'sus') => {
    setError('')
    try {
      if (kind === 'nasa' && nasaComplete) await api.post('/surveys/nasa-tlx', { project_id: projectId, ...nasaScores })
      if (kind === 'sus' && susComplete) await api.post('/surveys/sus', { project_id: projectId, scores: susScores })
      setSubmitted(true)
    } catch (caught: any) {
      setError(caught?.message || 'Invio non riuscito.')
    }
  }

  return (
    <section className="surface mt-6 p-4" aria-labelledby="survey-title">
      <h3 id="survey-title" className="mb-3 font-semibold">Questionari di ricerca</h3>
      <div className="mb-3 flex gap-2">
        <button onClick={() => { setActive('nasa'); setSubmitted(false) }} className={`rounded px-3 py-1 ${active === 'nasa' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}>NASA Raw-TLX</button>
        <button onClick={() => { setActive('sus'); setSubmitted(false) }} className={`rounded px-3 py-1 ${active === 'sus' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}>SUS</button>
      </div>

      {active === 'nasa' && <div>
        <h4 className="mb-2 font-medium">NASA Raw-TLX (carico cognitivo)</h4>
        {NASA_TLX_QUESTIONS.map((question) => <div key={question.key} className="mb-3">
          <label htmlFor={`nasa-${question.key}`} className="mb-1 block text-sm">{question.label}</label>
          <input id={`nasa-${question.key}`} type="range" min="0" max="100" step="5" value={nasaScores[question.key] ?? 50} onChange={(event) => setNasaScores({ ...nasaScores, [question.key]: Number(event.target.value) })} className="w-full accent-blue-600" />
          <div className="flex justify-between text-xs text-gray-500"><span>{question.low} (0)</span><strong>{nasaScores[question.key] ?? '—'}</strong><span>{question.high} (100)</span></div>
        </div>)}
        {!nasaComplete && <p className="text-xs text-slate-500">Valuta tutte le sei dimensioni per continuare.</p>}
        <button onClick={() => submit('nasa')} disabled={!nasaComplete} className="mt-2 rounded bg-green-600 px-3 py-1 text-white disabled:cursor-not-allowed disabled:opacity-50">Invia</button>
      </div>}

      {active === 'sus' && <div>
        <h4 className="mb-2 font-medium">SUS (Scala di usabilità del sistema)</h4>
        {SUS_QUESTIONS.map((question, index) => <fieldset key={question} className="mb-3">
          <legend className="mb-1 block text-sm">{index + 1}. {question}</legend>
          <div className="flex flex-wrap gap-3">{[1, 2, 3, 4, 5].map((value) => <label key={value} className="flex items-center gap-1 text-xs"><input type="radio" name={`sus-${index}`} value={value} checked={susScores[index] === value} onChange={() => { const scores = [...susScores]; scores[index] = value; setSusScores(scores) }} />{value}</label>)}</div>
        </fieldset>)}
        <p className="text-xs text-slate-500">1 = completamente in disaccordo · 5 = completamente d'accordo</p>
        <button onClick={() => submit('sus')} disabled={!susComplete} className="mt-2 rounded bg-green-600 px-3 py-1 text-white disabled:cursor-not-allowed disabled:opacity-50">Invia</button>
      </div>}
      {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
      {submitted && <p className="mt-2 text-sm text-green-600">Questionario inviato.</p>}
    </section>
  )
}
