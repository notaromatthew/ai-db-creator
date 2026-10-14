import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExamplesPage from './ExamplesPage'

const api = vi.hoisted(() => ({ get: vi.fn() }))
const auth = vi.hoisted(() => ({ authenticated: false, register: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))
vi.mock('@/context/KeycloakContext', () => ({ useAuth: () => auth }))

const renderPage = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ExamplesPage /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => { api.get.mockReset(); auth.authenticated = false })

describe('ExamplesPage', () => {
  it('mostra le tre schede con tabelle e relazioni e il link al dettaglio', async () => {
    api.get.mockResolvedValue({ examples: [
      { name: 'library', title: 'Biblioteca: prestiti', subtitle: 'Prestiti, iscritti e multe', icon: 'local_library', tables: 5, relationships: 4 },
      { name: 'university', title: 'Università: corsi', subtitle: 'Studenti e corsi', icon: 'school', tables: 3, relationships: 2 },
      { name: 'hospital', title: 'Ospedale: visite', subtitle: 'Visite e fatture', icon: 'local_hospital', tables: 8, relationships: 7 },
    ] })
    renderPage()
    expect(await screen.findByText('Biblioteca')).toBeInTheDocument()
    expect(screen.getByText('8 tabelle')).toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: /Apri l'esempio/i })
    expect(links).toHaveLength(3)
    expect(links[0]).toHaveAttribute('href', '/app/examples/library')
    expect(api.get).toHaveBeenCalledWith('/examples')
  })

  it('invita a creare un account solo se non si è autenticati', async () => {
    api.get.mockResolvedValue({ examples: [] })
    const { unmount } = renderPage()
    expect(await screen.findByRole('button', { name: /Crea un account/i })).toBeInTheDocument()
    unmount()
    auth.authenticated = true
    renderPage()
    await screen.findByText('Esempi già analizzati')
    expect(screen.queryByRole('button', { name: /Crea un account/i })).toBeNull()
  })

  it('mostra un errore se il caricamento fallisce', async () => {
    api.get.mockRejectedValue(new Error('rete'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/Non riesco a caricare/i)
  })
})
