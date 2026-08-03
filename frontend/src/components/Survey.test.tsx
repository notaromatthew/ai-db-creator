import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Survey from './Survey'

vi.mock('@/api/client', () => ({ api: { post: vi.fn().mockResolvedValue({}) } }))

describe('Survey research scales', () => {
  it('requires all NASA Raw-TLX dimensions and uses 0-100 step 5', async () => {
    render(<Survey projectId="p1" />)
    await userEvent.click(screen.getByRole('button', { name: /NASA Raw-TLX/i }))
    const sliders = screen.getAllByRole('slider')
    expect(sliders).toHaveLength(6)
    expect(sliders[0]).toHaveAttribute('min', '0')
    expect(sliders[0]).toHaveAttribute('max', '100')
    expect(sliders[0]).toHaveAttribute('step', '5')
    expect(screen.getByRole('button', { name: 'Invia' })).toBeDisabled()
  })

  it('shows the ten standard alternating SUS items and blocks incomplete submit', async () => {
    render(<Survey projectId="p1" />)
    await userEvent.click(screen.getByRole('button', { name: 'SUS' }))
    expect(screen.getAllByRole('radio')).toHaveLength(50)
    expect(screen.getByText(/inutilmente complesso/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Invia' })).toBeDisabled()
  })
})
