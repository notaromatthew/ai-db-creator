import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ResearchPage from './ResearchPage'
import { IntervalChart, METRIC_COLORS, METRIC_LABELS } from './charts'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))
const auth = vi.hoisted(() => ({ roles: ['aidb-researcher'] as string[], isAdmin: false }))
vi.mock('@/context/KeycloakContext', () => ({ useAuth: () => auth }))

const stat = (mean: number) => ({ n: 3, mean, low: mean - 0.1, high: mean + 0.1 })
const run = (over = {}) => ({
  id: 'r1', batch_id: 'b', dataset: 'university', condition: 'full_llm', provider: 'vertex', model: 'gemini-2.5-flash-lite', temperature: 0.5,
  run_index: 1, status: 'done', f1: 0.71, precision: 0.8, recall: 0.65, value_accuracy: 0.9, judge_score: 0.85, tokens_in: 1000, tokens_out: 500,
  cost_usd: 0.0003, latency_s: 4.2, error: null, created_at: '2026-10-10T10:00:00', started_at: null, finished_at: '2026-10-10T10:01:00', ...over,
})
const meta = {
  datasets: ['hospital', 'library', 'university'], conditions: ['full_llm', 'baseline'], temperatures: [0, 0.1, 0.5, 1], cost_cap_usd: 25, max_batch_runs: 60,
  models: [{ model: 'gemini-2.5-flash-lite', price_in_per_mtok: 0.1, price_out_per_mtok: 0.4, current: true }, { model: 'gemini-2.5-flash', price_in_per_mtok: 0.3, price_out_per_mtok: 2.5, current: false }],
  filters: { datasets: ['university'], conditions: ['full_llm'], models: ['gemini-2.5-flash-lite'], temperatures: [0.5] }, software_revision: 'abcd1234',
}
const group = {
  dataset: 'university', condition: 'full_llm', model: 'gemini-2.5-flash-lite', temperature: 0.5, n_runs: 3,
  f1: stat(0.7), precision: stat(0.8), recall: stat(0.6), value_accuracy: stat(0.9), judge_score: stat(0.85),
  cost_usd_mean: 0.0003, cost_usd_total: 0.0009, latency_s_mean: 4.2, tokens_in_mean: 1000, tokens_out_mean: 500,
}
let estimate: Record<string, unknown>

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset())
  auth.roles = ['aidb-researcher']; auth.isAdmin = false
  estimate = { runs: 3, tokens_in: 9000, tokens_out: 18000, cost_usd: 0.0081, cap_usd: 25, over_cap: false, approximate: true }
  api.get.mockImplementation((path: string) => {
    if (path === '/research/meta') return Promise.resolve(meta)
    if (path.startsWith('/research/runs/r1')) return Promise.resolve({ ...run(), per_table: { studenti: { f1: 0.7, precision: 0.8, recall: 0.6, total_cells: 40 } },
      schema: { tables: [{ name: 'student', columns: [{ name: 'id' }, { name: 'nome' }] }] }, manifest: { software_revision: 'abcd1234', dataset_hash: 'h'.repeat(8), research_mode: true } })
    if (path.startsWith('/research/runs')) return Promise.resolve({ runs: [run(), run({ id: 'r2', run_index: 2, f1: null, status: 'failed' })] })
    if (path.startsWith('/research/summary')) return Promise.resolve({ groups: [group] })
    if (path.startsWith('/research/queue')) return Promise.resolve({ active: [run({ id: 'q1', status: 'running' }), run({ id: 'q2', status: 'queued', run_index: 2 })], recent: [], queued: 1, running: 1 })
    if (path.startsWith('/research/diagnosis')) return Promise.resolve({ available: true, n_runs: 4, best: [{ id: 'a', run_index: 1, f1: 0.9, model: 'm' }], worst: [{ id: 'b', run_index: 2, f1: 0.4, model: 'm' }],
      per_table: [{ table: 'corsi', f1_best: 0.9, f1_worst: 0.3, delta: 0.6, schema_loss_worst: 0.5, population_loss_worst: 0.2 }],
      attribution: { schema_share: 0.7, population_share: 0.3, verdict: 'schema', note: 'Approssimazione.' } })
    if (path.startsWith('/research/export')) return Promise.resolve({ filename: 'run-ricerca.csv', mime: 'text/csv', content: 'a,b\n' })
    if (path === '/study/admin/status') return Promise.resolve({ arms: [{ arm: 'manual', enrolled: 3, active: 2, completed: 1, withdrawn: 1, target: 20 }], total: 3, balanced: true, consent_version: '1.0' })
    return Promise.resolve({})
  })
  api.post.mockImplementation((path: string) => {
    if (path === '/research/estimate') return Promise.resolve(estimate)
    if (path === '/research/batches') return Promise.resolve({ batch_id: 'b', runs: 3 })
    return Promise.resolve({ status: 'cancelled' })
  })
})

const tab = (name: string) => userEvent.click(screen.getByRole('tab', { name: new RegExp(name) }))

describe('ResearchPage', () => {
  it('chi non è ricercatore né admin non vede nulla e non chiama il server', () => {
    auth.roles = []
    render(<ResearchPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Area riservata alla ricerca')
    expect(api.get).not.toHaveBeenCalled()
  })

  it('un admin entra', async () => {
    auth.roles = []; auth.isAdmin = true
    render(<ResearchPage />)
    expect(await screen.findByRole('heading', { name: 'Ricerca' })).toBeInTheDocument()
  })

  it('tabella dei run con filtri e dettaglio con schema, metriche e manifesto', async () => {
    render(<ResearchPage />)
    expect(await screen.findByText('abcd1234')).toBeInTheDocument()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByText('0,710')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Temperatura'), '0.5')
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/research/runs?temperature=0.5'))
    await userEvent.selectOptions(screen.getByLabelText('Dataset'), 'university')
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/research/runs?dataset=university&temperature=0.5'))
    await userEvent.click(screen.getAllByRole('button', { name: /Dettaglio del run/ })[0])
    const detail = await screen.findByRole('region', { name: 'Dettaglio del run' })
    expect(within(detail).getByText('student')).toBeInTheDocument()
    expect(within(detail).getByText('id, nome')).toBeInTheDocument()
    expect(within(detail).getByText('studenti')).toBeInTheDocument()
    expect(within(detail).getByText(/"software_revision": "abcd1234"/)).toBeInTheDocument()
  })

  it('esporta CSV e JSON con i filtri attivi', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    render(<ResearchPage />)
    await screen.findByRole('table')
    await userEvent.click(screen.getByRole('button', { name: /Esporta CSV/ }))
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/research/export?format=csv&wrap=1'))
    await userEvent.click(screen.getByRole('button', { name: /Esporta JSON/ }))
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/research/export?format=json&wrap=1'))
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2)
  })

  it('confronti: grafici SVG con intervalli, giudice accanto all\'F1 e costo/latenza', async () => {
    render(<ResearchPage />)
    await tab('Confronti')
    const charts = await screen.findAllByRole('img')
    expect(charts).toHaveLength(2)
    expect(charts[0]).toHaveAccessibleName(/F1, precisione e richiamo/)
    expect(charts[1]).toHaveAccessibleName(/giudice LLM/)
    expect(charts[1].querySelectorAll('circle')).toHaveLength(3)
    expect(screen.getAllByText('Mostra i valori in tabella')).toHaveLength(2)
    expect(screen.getByText(/Costo e latenza/)).toBeInTheDocument()
    expect(screen.getByText('4,2 s')).toBeInTheDocument()
    expect(screen.getAllByText(/0,700 \[0,600; 0,800\] n=3/).length).toBeGreaterThan(0)
  })

  it('lancio: stima prima dell\'avvio, conferma obbligatoria, invio con confirm_cost', async () => {
    render(<ResearchPage />)
    await tab('Lancio e coda')
    expect(await screen.findByText(/Stima prima dell'avvio: 3 run/)).toBeInTheDocument()
    const start = screen.getByRole('button', { name: 'Avvia i run' })
    expect(start).toBeDisabled()
    expect(api.post).toHaveBeenCalledWith('/research/estimate', { datasets: ['hospital'], conditions: ['full_llm'], model: 'gemini-2.5-flash-lite', temperatures: [0.5], runs: 3 })
    await userEvent.selectOptions(screen.getByLabelText('Modello'), 'gemini-2.5-flash')
    await userEvent.click(screen.getByLabelText('1'))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/research/estimate', expect.objectContaining({ model: 'gemini-2.5-flash', temperatures: [0.5, 1] })))
    await userEvent.click(await screen.findByLabelText(/Ho letto la stima del costo/))
    await userEvent.click(start)
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/research/batches', { datasets: ['hospital'], conditions: ['full_llm'], model: 'gemini-2.5-flash', temperatures: [0.5, 1], runs: 3, confirm_cost: true }))
    expect(await screen.findByText('Messi in coda 3 run.')).toBeInTheDocument()
  })

  it('lancio: oltre il tetto non si può avviare', async () => {
    estimate = { ...estimate, over_cap: true, cost_usd: 99 }
    render(<ResearchPage />)
    await tab('Lancio e coda')
    expect(await screen.findByText(/supera il tetto/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Ho letto la stima del costo/)).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Avvia i run' })).toBeDisabled()
  })

  it('coda: stato dei lavori e annullamento', async () => {
    render(<ResearchPage />)
    await tab('Lancio e coda')
    expect(await screen.findByText('1 in corso, 1 in attesa.')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: /Annulla il run/ })[1])
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/research/runs/q2/cancel', {}))
  })

  it('diagnosi: attribuzione a schema o popolamento e tabella per tabella', async () => {
    render(<ResearchPage />)
    await tab('Diagnosi')
    expect(await screen.findByText('La perdita dipende soprattutto dallo schema generato.')).toBeInTheDocument()
    expect(screen.getByText(/Schema: 70%/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Schema 70 per cento/ })).toBeInTheDocument()
    expect(screen.getByText('corsi')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/research/diagnosis?dataset=university&condition=full_llm&temperature=0.5')
  })

  it('studio: stato dei bracci e cancellazione su richiesta con conferma', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<ResearchPage />)
    await tab('Studio')
    expect(await screen.findByText('Manuale (senza IA)')).toBeInTheDocument()
    expect(screen.getByText(/I bracci sono bilanciati/)).toBeInTheDocument()
    const erase = screen.getByRole('button', { name: 'Cancella i dati' })
    expect(erase).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Codice del partecipante'), 'AB12C-D34EF')
    await userEvent.click(erase)
    expect(confirm).toHaveBeenCalled()
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/study/admin/erase', { code: 'AB12C-D34EF' }))
    URL.createObjectURL = vi.fn(() => 'blob:x'); URL.revokeObjectURL = vi.fn()
    await userEvent.click(screen.getByRole('button', { name: 'Eventi' }))
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/study/admin/export?kind=events&wrap=1'))
  })
})

describe('IntervalChart', () => {
  it('disegna punto e barra per ogni metrica e mostra un messaggio senza dati', () => {
    const { container, rerender } = render(<IntervalChart title="Prova" rows={[{ label: 'g', series: ['f1', 'recall'].map((k) => ({ key: k, label: METRIC_LABELS[k], color: METRIC_COLORS[k], stat: stat(0.5) })) }]} />)
    expect(container.querySelectorAll('circle')).toHaveLength(2)
    expect(screen.getByRole('img', { name: 'Prova' })).toBeInTheDocument()
    rerender(<IntervalChart title="Prova" rows={[]} />)
    expect(screen.getByText(/Nessun dato da mostrare/)).toBeInTheDocument()
  })
})
