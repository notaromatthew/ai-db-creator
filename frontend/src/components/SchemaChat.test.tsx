import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SchemaChat from './SchemaChat'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))

const schema = { tables: [], relationships: [], description: '' } as any

const renderChat = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <SchemaChat projectId="p1" schema={schema} documentIds={[]} />
  </QueryClientProvider>,
)

beforeEach(() => { Object.values(api).forEach((fn) => fn.mockReset()) })

describe('SchemaChat', () => {
  it('mostra il markdown reso e non applica nulla finche non confermi', async () => {
    api.get.mockResolvedValue({ messages: [] })
    api.post.mockResolvedValue({ response: 'Aggiungo **email** ai clienti.\n- nuova colonna\nVuoi che le applichi?', proposal: true, schema: null })
    renderChat()
    fireEvent.change(await screen.findByLabelText("Messaggio all'IA"), { target: { value: 'aggiungi email' } })
    fireEvent.click(screen.getByRole('button', { name: 'Invia' }))
    expect(await screen.findByText('email')).toBeInTheDocument()
    expect(screen.getByText('email').tagName).toBe('STRONG')
    expect(document.body.textContent).not.toContain('**')
    expect(await screen.findByRole('button', { name: 'Applica le modifiche' })).toBeInTheDocument()
    expect(api.put).not.toHaveBeenCalled()
  })

  it('con "Applica le modifiche" chiede lo schema aggiornato e lo salva', async () => {
    api.get.mockResolvedValue({ messages: [{ role: 'assistant', content: 'Aggiungo la data. Vuoi che le applichi?', proposal: true }] })
    api.post.mockResolvedValue({ response: 'ok', schema: { tables: [{ name: 'ordini', columns: [] }], relationships: [] } })
    api.put.mockResolvedValue({})
    renderChat()
    fireEvent.click(await screen.findByRole('button', { name: 'Applica le modifiche' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/projects/p1/schema', expect.objectContaining({ tables: expect.any(Array) })))
    expect(api.post).toHaveBeenCalledWith('/projects/p1/chat/apply', {})
    expect(await screen.findByText(/Ho aggiornato lo schema/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Applica le modifiche' })).toBeNull()
  })

  it('"Non ora" scarta la proposta senza toccare lo schema', async () => {
    api.get.mockResolvedValue({ messages: [{ role: 'assistant', content: 'Proposta. Vuoi che le applichi?', proposal: true }] })
    api.post.mockResolvedValue({ dismissed: true })
    renderChat()
    fireEvent.click(await screen.findByRole('button', { name: 'Non ora' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/projects/p1/chat/dismiss', {}))
    expect(api.put).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Applica le modifiche' })).toBeNull()
  })

  it('se scrivi "sì" e il server conferma l applicazione, salva lo schema ricevuto', async () => {
    api.get.mockResolvedValue({ messages: [{ role: 'assistant', content: 'Proposta. Vuoi che le applichi?', proposal: true }] })
    api.post.mockResolvedValue({ response: 'Perfetto, applico le modifiche.', proposal: false, schema: { tables: [{ name: 'x', columns: [] }], relationships: [] } })
    api.put.mockResolvedValue({})
    renderChat()
    fireEvent.change(await screen.findByLabelText("Messaggio all'IA"), { target: { value: 'sì' } })
    fireEvent.click(screen.getByRole('button', { name: 'Invia' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/projects/p1/schema', expect.any(Object)))
  })
})
