import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import JobProgress from './JobProgress'
import OcrNotice from './OcrNotice'
import QueryHistoryList from './QueryHistoryList'
import SchemaStatusBadge from './SchemaStatusBadge'
import SchemaVersionsPanel from './SchemaVersionsPanel'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))

const wrap = (ui: React.ReactNode) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>,
)

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('JobProgress', () => {
  it('espone l\'avanzamento ai lettori di schermo e permette di annullare', () => {
    const onCancel = vi.fn()
    render(<JobProgress job={{ id: 'j', project_id: 'p', kind: 'dati', status: 'running', progress: 42 }} title="Sto inserendo i dati" onCancel={onCancel} />)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42')
    expect(screen.getByRole('status')).toHaveTextContent('In corso: 42%')
    fireEvent.click(screen.getByRole('button', { name: /annulla/i }))
    expect(onCancel).toHaveBeenCalled()
  })
})

describe('SchemaStatusBadge', () => {
  it('mostra bozza o definitivo con il numero di versione', () => {
    const { rerender } = render(<SchemaStatusBadge finalized={false} version={3} />)
    expect(screen.getByText(/Bozza/)).toHaveTextContent('versione 3')
    rerender(<SchemaStatusBadge finalized version={4} />)
    expect(screen.getByText(/Definitivo/)).toHaveTextContent('versione 4')
  })
})

describe('OcrNotice', () => {
  it('avvisa solo per i documenti che hanno bisogno di OCR', () => {
    const { container, rerender } = render(<OcrNotice documents={[{ id: '1', filename: 'a.pdf', needs_ocr: false }]} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<OcrNotice documents={[{ id: '2', filename: 'scansione.pdf', needs_ocr: true }]} />)
    expect(screen.getByRole('note')).toHaveTextContent('scansione.pdf')
  })
})

describe('SchemaVersionsPanel', () => {
  const versions = {
    current: 2, finalized: false,
    versions: [
      { version: 2, author: 'giulia', origin: 'chat', created_at: '2026-01-02T10:00:00', table_count: 3 },
      { version: 1, author: 'giulia', origin: 'generazione', created_at: '2026-01-01T10:00:00', table_count: 2 },
    ],
  }

  it('elenca le versioni e ripristina solo dopo conferma', async () => {
    api.get.mockResolvedValue(versions)
    api.post.mockResolvedValue({ schema: { tables: [], relationships: [] }, schema_version: 3, restored_from: 1 })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    wrap(<SchemaVersionsPanel projectId="p1" />)
    const restore = await screen.findByRole('button', { name: /ripristina la versione 1/i })
    expect(screen.queryByRole('button', { name: /ripristina la versione 2/i })).toBeNull()
    fireEvent.click(restore)
    expect(api.post).not.toHaveBeenCalled()
    fireEvent.click(restore)
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/projects/p1/schema/versions/1/restore', {}))
    expect(await screen.findByText(/ripristinato la versione 1/i)).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('blocca il ripristino se lo schema è definitivo', async () => {
    api.get.mockResolvedValue({ ...versions, finalized: true })
    wrap(<SchemaVersionsPanel projectId="p1" />)
    expect(await screen.findByRole('button', { name: /ripristina la versione 1/i })).toBeDisabled()
  })
})

describe('QueryHistoryList', () => {
  it('ricarica l\'elenco e ripropone la domanda scelta', async () => {
    const item = { id: 1, question: 'Quanti clienti ho?', sql: 'SELECT COUNT(*) FROM clienti', source: 'query', outcome: 'ok', rows: 1, created_at: '2026-01-01T10:00:00' }
    api.get.mockResolvedValue({ queries: [item] })
    const onPick = vi.fn()
    wrap(<QueryHistoryList projectId="p1" onPick={onPick} />)
    fireEvent.click(await screen.findByRole('button', { name: /quanti clienti ho/i }))
    expect(api.get).toHaveBeenCalledWith('/projects/p1/queries')
    expect(onPick).toHaveBeenCalledWith(item)
  })
})
