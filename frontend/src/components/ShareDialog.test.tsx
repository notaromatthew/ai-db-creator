import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ShareDialog from './ShareDialog'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))

const sharing = {
  owner: { id: 'o', email: 'giulia@esempio.it', name: 'Giulia Rossi' },
  members: [{ user_id: 'u2', email: 'marco@esempio.it', name: 'Marco Bianchi', role: 'viewer' }],
  invites: [{ id: 'i1', email: 'nuova@esempio.it', role: 'editor', expires_at: '2030-01-10T10:00:00' }],
  links: [],
}

beforeEach(() => {
  sessionStorage.clear()
  Object.values(api).forEach((fn) => fn.mockReset())
  api.get.mockResolvedValue(sharing)
  api.post.mockResolvedValue({})
  api.put.mockResolvedValue({})
  api.delete.mockResolvedValue({})
})

describe('ShareDialog', () => {
  it('non mostra nulla se chiuso e si presenta come dialogo modale', async () => {
    const { rerender } = render(<ShareDialog projectId="p1" open={false} onClose={() => {}} />)
    expect(screen.queryByRole('dialog')).toBeNull()
    rerender(<ShareDialog projectId="p1" open onClose={() => {}} />)
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(await screen.findByText('Marco Bianchi')).toBeInTheDocument()
    expect(screen.getByText('In attesa')).toBeInTheDocument()
  })

  it('invita per email con il ruolo scelto', async () => {
    api.post.mockResolvedValueOnce({ status: 'invited', email: 'ada@esempio.it', role: 'viewer' })
    render(<ShareDialog projectId="p1" open onClose={() => {}} />)
    await screen.findByText('Marco Bianchi')
    await userEvent.type(screen.getByLabelText(/Invita con l'email/i), 'ada@esempio.it')
    await userEvent.selectOptions(screen.getByLabelText("Ruolo dell'invitato"), 'viewer')
    await userEvent.click(screen.getByRole('button', { name: 'Invita' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/projects/p1/invites', { email: 'ada@esempio.it', role: 'viewer' }))
    expect(await screen.findByText(/si attiva appena si registra/i)).toBeInTheDocument()
  })

  it('cambia il ruolo di un membro', async () => {
    render(<ShareDialog projectId="p1" open onClose={() => {}} />)
    const row = (await screen.findAllByTestId('member-row'))[0]
    await userEvent.selectOptions(within(row).getByRole('combobox'), 'editor')
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/projects/p1/members/u2', { role: 'editor' }))
  })

  it('crea il link pubblico e mostra l\'URL completo una volta', async () => {
    api.post.mockResolvedValueOnce({ token: 'abc', path: '/app/shared/abc', expires_in_days: 30 })
    render(<ShareDialog projectId="p1" open onClose={() => {}} />)
    await screen.findByText('Marco Bianchi')
    await userEvent.click(screen.getByRole('button', { name: /Crea un link pubblico/i }))
    const input = await screen.findByLabelText('Link pubblico')
    expect(input).toHaveValue(window.location.origin + '/app/shared/abc')
    expect(api.post).toHaveBeenCalledWith('/projects/p1/links', {})
  })

  it('si chiude con Esc', async () => {
    const onClose = vi.fn()
    render(<ShareDialog projectId="p1" open onClose={onClose} />)
    await screen.findByText('Marco Bianchi')
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('conserva in sessione l\'email in compilazione e la ripropone alla riapertura', async () => {
    const first = render(<ShareDialog projectId="p1" open onClose={() => {}} />)
    await screen.findByText('Marco Bianchi')
    await userEvent.type(screen.getByLabelText(/Invita con l'email/i), 'ada@esempio.it')
    first.unmount()
    render(<ShareDialog projectId="p1" open onClose={() => {}} />)
    expect(await screen.findByLabelText(/Invita con l'email/i)).toHaveValue('ada@esempio.it')
  })
})
