import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminPage from './AdminPage'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))

const links = [{ id: 'l1', project_id: 'p1', project_name: 'Biblioteca', created_by: 'ada@esempio.it', expires_at: '2030-01-10T10:00:00' }]
let settings: Record<string, unknown>
let linkReply: () => Promise<unknown>

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><AdminPage /></QueryClientProvider>)
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  settings = { default_daily_ai_quota: 20, daily_ai_budget_total: 500, max_upload_mb: 25, max_projects_per_user: 10, registration_open: true, maintenance_message: '', ai_enabled: true }
  linkReply = () => Promise.resolve(links)
  api.put.mockResolvedValue({})
  api.delete.mockResolvedValue({})
  api.get.mockImplementation((path: string) => {
    if (path === '/admin/overview') return Promise.resolve({ users: 3, projects: 5, ai_calls_today: 2, daily_budget: 500, research_mode: false, llm_provider: 'vertex' })
    if (path === '/admin/settings') return Promise.resolve(settings)
    if (path === '/admin/links') return linkReply()
    if (path.startsWith('/admin/usage?group=day')) return Promise.resolve([{ key: '2030-01-02', count: 4 }])
    if (path.startsWith('/admin/usage?group=kind')) return Promise.resolve([{ key: 'chat', count: 3 }])
    if (path.startsWith('/admin/usage?group=user')) return Promise.resolve([{ key: 'ada@esempio.it', count: 4 }])
    return Promise.resolve([])
  })
})

describe('AdminPage', () => {
  it('l\'interruttore delle chiamate AI chiede conferma e salva ai_enabled', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    const toggle = await screen.findByRole('switch', { name: 'Chiamate AI attive' })
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(toggle)
    expect(confirm).toHaveBeenCalled()
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/admin/settings', { ai_enabled: false }))
    confirm.mockRestore()
  })

  it('senza conferma non cambia nulla', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await userEvent.click(await screen.findByRole('switch', { name: 'Chiamate AI attive' }))
    expect(api.put).not.toHaveBeenCalled()
    confirm.mockRestore()
  })

  it('elenca i link pubblici e li revoca dopo conferma', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await userEvent.click(await screen.findByRole('tab', { name: 'Link pubblici' }))
    expect(await screen.findByText('Biblioteca')).toBeInTheDocument()
    expect(screen.getByText(/ada@esempio.it/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /revoca il link di biblioteca/i }))
    await waitFor(() => expect(api.delete).toHaveBeenCalledWith('/admin/links/l1'))
    expect(await screen.findByText(/revocato/i)).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('mostra stato di caricamento ed errore dei link', async () => {
    linkReply = () => Promise.reject(new Error('Non autorizzato'))
    renderPage()
    await userEvent.click(await screen.findByRole('tab', { name: 'Link pubblici' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Non autorizzato')
  })

  it('mostra i consumi per giorno, tipo e utente', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('tab', { name: 'Uso e costi' }))
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/admin/usage?group=user&days=14'))
    const byUser = await screen.findByRole('region', { name: /per utente/i })
    expect(await within(byUser).findByText('ada@esempio.it')).toBeInTheDocument()
    expect(await screen.findByText('Chat sullo schema')).toBeInTheDocument()
  })
})
