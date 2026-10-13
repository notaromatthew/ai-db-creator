import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import StudyPage from './StudyPage'

vi.mock('@/api/client', () => ({ api: { post: vi.fn().mockResolvedValue({}) } }))

describe('StudyPage', () => {
  it('shows tasks only after both consent boxes are checked', async () => {
    render(<MemoryRouter><StudyPage /></MemoryRouter>)
    expect(screen.queryByText(/Compito 1/)).toBeNull()
    const boxes = screen.getAllByRole('checkbox')
    await userEvent.click(boxes[0])
    expect(screen.queryByText(/Compito 1/)).toBeNull()
    await userEvent.click(boxes[1])
    expect(screen.getByText(/Compito 1/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'NASA Raw-TLX' })).toBeInTheDocument()
  })
})
