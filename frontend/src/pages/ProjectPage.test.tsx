import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectPage from './ProjectPage'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), postFile: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))
vi.mock('@/config/AppConfig', () => ({ useConfig: () => ({ config: { research_mode: false } }) }))
vi.mock('@/components/DocumentUploader', () => ({ default: () => <div>uploader</div> }))
vi.mock('@/components/SchemaDiagram', () => ({ default: () => <div>diagramma</div> }))
vi.mock('@/components/SchemaViewer', () => ({ default: () => <div>tabelle</div> }))
vi.mock('@/components/SchemaChat', () => ({ default: () => <div>chat</div> }))
vi.mock('@/components/ShareDialog', () => ({ default: () => null }))

const project = { id: 'p1', name: 'Ordini', my_role: 'owner', schema_version: 2, target_dialect: 'oracle', prompt: '' }
const routes = (jobs: any[], extra: Record<string, any> = {}) => {
  api.get.mockImplementation(async (path: string) => {
    if (path in extra) return extra[path]
    if (path === '/projects/p1') return project
    if (path === '/projects/p1/jobs') return { jobs }
    if (path === '/projects/p1/documents') return [{ id: 'd1', filename: 'scan.pdf', needs_ocr: true }]
    if (path === '/projects/p1/data/stats') return {}
    if (path === '/projects/p1/schema') return { tables: [], relationships: [] }
    return []
  })
}

const renderPage = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={['/app/p1']}>
      <Routes><Route path="/app/:id" element={<ProjectPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('ProjectPage lavori', () => {
  it('riprende un lavoro schema in corso alla riapertura e lo annulla', async () => {
    routes([{ id: 'j1', kind: 'schema', status: 'running', progress: 55 }])
    api.post.mockResolvedValue({ id: 'j1', status: 'cancelled' })
    renderPage()
    const bar = await screen.findByRole('progressbar', { name: /avanzamento/i })
    expect(bar).toHaveAttribute('aria-valuenow', '55')
    fireEvent.click(screen.getByRole('button', { name: /annulla la generazione/i }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/projects/p1/jobs/j1/cancel', {}))
  })

  it('avvia la generazione come lavoro e mostra badge e avviso OCR', async () => {
    routes([])
    api.post.mockResolvedValue({ id: 'j2', kind: 'schema', status: 'queued', progress: 0 })
    renderPage()
    expect(await screen.findByRole('note')).toHaveTextContent('scan.pdf')
    fireEvent.click(screen.getByRole('button', { name: /genera lo schema/i }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/projects/p1/jobs', expect.objectContaining({ kind: 'schema', document_ids: ['d1'] })))
  })

  it('mostra un errore leggibile se il lavoro è fallito', async () => {
    routes([{ id: 'j3', kind: 'schema', status: 'failed', progress: 10, error: 'Il modello non ha risposto.', updated_at: new Date().toISOString() }])
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Il modello non ha risposto.')
  })
})
