import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Dashboard from './Dashboard'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))
vi.mock('@/context/KeycloakContext', () => ({ useAuth: () => ({ username: 'giulia', authenticated: true, isAdmin: false }) }))

const project = (over: Record<string, unknown>) => ({
  id: 'p', name: 'Progetto', created_at: '', updated_at: '', my_role: 'owner', status: 'not_started', step: 1, document_count: 0, table_count: 0, ...over,
})

const renderDashboard = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><Dashboard /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('Dashboard', () => {
  it('mostra lo stato vuoto con invito a creare il primo progetto', async () => {
    api.get.mockResolvedValue([])
    renderDashboard()
    expect(await screen.findByText('Non hai ancora progetti')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crea il primo progetto/i })).toBeInTheDocument()
    expect(screen.queryByText('Condivisi con me')).toBeNull()
  })

  it('separa i miei progetti da quelli condivisi e mostra ruolo e stato', async () => {
    api.get.mockResolvedValue([
      project({ id: 'a', name: 'Ordini clienti', status: 'schema_review', step: 2, table_count: 4 }),
      project({ id: 'b', name: 'Biblioteca', my_role: 'editor', owner_name: 'Marco', status: 'data_ready', step: 3 }),
      project({ id: 'c', name: 'Magazzino', my_role: 'viewer' }),
    ])
    renderDashboard()
    expect(await screen.findByText('Condivisi con me')).toBeInTheDocument()
    expect(screen.getByText('Proprietario')).toBeInTheDocument()
    expect(screen.getByText('Editor')).toBeInTheDocument()
    expect(screen.getByText('Lettore')).toBeInTheDocument()
    expect(screen.getByText('Schema da rivedere')).toBeInTheDocument()
    expect(screen.getByText('Dati pronti')).toBeInTheDocument()
    expect(screen.getByText(/Prossimo passo: controlla lo schema di/i)).toBeInTheDocument()
    // elimina solo per il proprietario, "Lascia" solo per i condivisi
    expect(screen.getAllByRole('button', { name: /^Elimina /i })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: /Lascia il progetto/i })).toHaveLength(2)
  })
})
