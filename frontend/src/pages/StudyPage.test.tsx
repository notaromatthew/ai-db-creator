import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudyPage from './StudyPage'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))

let arm = 'ai_only'

beforeEach(() => {
  Object.values(api).forEach((f) => f.mockReset())
  sessionStorage.clear()
  arm = 'ai_only'
  api.post.mockImplementation((path: string) => {
    if (path === '/study/participants') return Promise.resolve({ participant_id: 'abc123', code: 'AB12C-D34EF', arm, step: 'task' })
    if (path.endsWith('/task/complete')) return Promise.resolve({ step: 'tlx' })
    if (path.endsWith('/nasa-tlx')) return Promise.resolve({ step: 'sus', score: 50 })
    if (path.endsWith('/sus')) return Promise.resolve({ step: 'debrief', score: 75 })
    if (path.endsWith('/debrief')) return Promise.resolve({ step: 'done' })
    if (path.endsWith('/withdraw')) return Promise.resolve({ status: 'withdrawn' })
    return Promise.resolve({ status: 'saved' })
  })
  api.put.mockResolvedValue({ status: 'saved', schema_hash: 'x' })
})

const renderPage = () => render(<MemoryRouter><StudyPage /></MemoryRouter>)

async function consentAndEnroll() {
  renderPage()
  const next = await screen.findByRole('button', { name: /Continua/ })
  expect(next).toBeDisabled()
  const boxes = screen.getAllByRole('checkbox')
  await userEvent.click(boxes[0])
  expect(next).toBeDisabled()
  await userEvent.click(boxes[1])
  expect(next).toBeEnabled()
  await userEvent.click(next)
  const start = await screen.findByRole('button', { name: 'Inizia lo studio' })
  expect(start).toBeDisabled()
  await userEvent.selectOptions(screen.getByLabelText('La tua fascia di età'), '25-34')
  await userEvent.selectOptions(screen.getByLabelText('Il tuo ruolo'), 'studente')
  const radios = screen.getAllByRole('radio')
  await userEvent.click(radios[2]) // esperienza database = 3
  await userEvent.click(radios[9]) // esperienza IA = 5
  expect(start).toBeEnabled()
  await userEvent.click(start)
}

describe('StudyPage (percorso del partecipante)', () => {
  it('mostra l\'informativa e non va avanti senza entrambi i consensi', async () => {
    renderPage()
    expect(await screen.findByText('Informativa e consenso')).toBeInTheDocument()
    expect(screen.getByText(/Non raccogliamo nome, email né indirizzo IP/)).toBeInTheDocument()
    expect(screen.queryByText(/Il tuo compito/)).toBeNull()
  })

  it('invia consenso e questionario demografico e mostra il codice una sola volta', async () => {
    await consentAndEnroll()
    expect(api.post).toHaveBeenCalledWith('/study/participants', {
      consent: true, consent_version: '1.0',
      demographics: { age_band: '25-34', role: 'studente', db_experience: 3, ai_experience: 5 },
    })
    expect(await screen.findByLabelText('Codice di ritiro')).toHaveTextContent('AB12C-D34EF')
    await userEvent.click(screen.getByRole('button', { name: /Ho annotato il codice/ }))
    expect(await screen.findByText('Il tuo compito')).toBeInTheDocument()
    expect(screen.getByText('Lavora con l\'assistente')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Apri l'app/ })).toHaveAttribute('href', '/app')
    expect(screen.queryByText('Editor dello schema')).toBeNull()
  })

  it('percorre compito, NASA-TLX, SUS e debrief fino alla fine', async () => {
    await consentAndEnroll()
    await userEvent.click(await screen.findByRole('button', { name: /Ho annotato il codice/ }))
    await userEvent.click(await screen.findByRole('button', { name: 'Ho finito il compito' }))
    expect(api.post).toHaveBeenCalledWith('/study/participants/abc123/task/complete', { code: 'AB12C-D34EF' })

    const submitTlx = await screen.findByRole('button', { name: 'Continua' })
    expect(submitTlx).toBeDisabled()
    for (const slider of screen.getAllByRole('slider')) fireEvent.change(slider, { target: { value: '40' } })
    expect(submitTlx).toBeEnabled()
    await userEvent.click(submitTlx)
    expect(api.post).toHaveBeenCalledWith('/study/participants/abc123/nasa-tlx', expect.objectContaining({
      code: 'AB12C-D34EF', mental_demand: 40, frustration: 40,
    }))

    const submitSus = await screen.findByRole('button', { name: 'Continua' })
    expect(submitSus).toBeDisabled()
    for (let i = 1; i <= 10; i++) await userEvent.click(screen.getByLabelText(`Domanda ${i}, risposta 4`))
    await userEvent.click(submitSus)
    expect(api.post).toHaveBeenCalledWith('/study/participants/abc123/sus', { code: 'AB12C-D34EF', scores: Array(10).fill(4) })

    await userEvent.type(await screen.findByLabelText(/Vuoi aggiungere un commento/), 'Tutto chiaro')
    await userEvent.click(screen.getByRole('button', { name: 'Concludi lo studio' }))
    expect(await screen.findByText('Grazie, hai finito')).toBeInTheDocument()
  })

  it('il braccio manuale ha l\'editor di schema e conclude solo dopo aver salvato', async () => {
    arm = 'manual'
    await consentAndEnroll()
    await userEvent.click(await screen.findByRole('button', { name: /Ho annotato il codice/ }))
    expect(await screen.findByRole('region', { name: 'Editor dello schema' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Apri l'app/ })).toBeNull()
    const finish = screen.getByRole('button', { name: 'Ho finito il compito' })
    expect(finish).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Nome della tabella'), 'libri')
    await userEvent.type(screen.getByLabelText('Nome colonna 1 della tabella 1'), 'id')
    await userEvent.click(screen.getByRole('button', { name: 'Salva lo schema' }))
    await waitFor(() => expect(api.put).toHaveBeenCalled())
    expect(api.put).toHaveBeenCalledWith('/study/participants/abc123/schema', {
      code: 'AB12C-D34EF',
      tables: [{ name: 'libri', columns: [{ name: 'id', type: 'TEXT', primary_key: false, nullable: true, references: null }] }],
    })
    await waitFor(() => expect(finish).toBeEnabled())
  })

  it('il ritiro cancella la sessione e conferma', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await consentAndEnroll()
    await userEvent.click(await screen.findByRole('button', { name: /Ho annotato il codice/ }))
    await userEvent.click(await screen.findByRole('button', { name: /Ritira la mia partecipazione/ }))
    expect(api.post).toHaveBeenCalledWith('/study/participants/abc123/withdraw', { code: 'AB12C-D34EF' })
    expect(await screen.findByText('Ti sei ritirato')).toBeInTheDocument()
    expect(sessionStorage.getItem('aidb.study.v1')).toBeNull()
  })

  it('riprende dal passo salvato nella scheda', async () => {
    sessionStorage.setItem('aidb.study.v1', JSON.stringify({ id: 'abc123', code: 'AB12C-D34EF', arm: 'ai_only' }))
    api.post.mockImplementation((path: string) => path.endsWith('/state') ? Promise.resolve({ step: 'sus' }) : Promise.resolve({}))
    renderPage()
    expect(await screen.findByText(/Quanto è stato facile da usare/)).toBeInTheDocument()
  })
})
