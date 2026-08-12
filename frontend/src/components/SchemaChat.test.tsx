import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SchemaChat from './SchemaChat'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: { post: vi.fn(), put: vi.fn() },
}))

const proposedSchema = {
  tables: [{ name: 'prodotti', columns: [{ name: 'id', data_type: 'INTEGER', is_primary_key: true }] }],
  relationships: [],
}

describe('SchemaChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('accepts a chat proposal through the chat acceptance endpoint', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ response: 'Ho preparato lo schema.', schema: proposedSchema })
      .mockResolvedValueOnce(proposedSchema)

    render(
      <QueryClientProvider client={new QueryClient()}>
        <SchemaChat projectId="project-1" schema={null} documentIds={[]} />
      </QueryClientProvider>,
    )

    await userEvent.type(screen.getByPlaceholderText('Scrivi un messaggio...'), 'Crea un catalogo')
    await userEvent.click(screen.getByRole('button', { name: 'Invia' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Accetta Schema' }))

    expect(api.post).toHaveBeenNthCalledWith(2, '/projects/project-1/chat-accept', proposedSchema)
    expect(api.put).not.toHaveBeenCalled()
    expect(await screen.findByText(/Schema accettato e salvato/)).toBeInTheDocument()
  })
})
