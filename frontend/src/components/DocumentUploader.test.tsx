import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DocumentUploader from './DocumentUploader'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({ api: { get: vi.fn(), postFile: vi.fn(), delete: vi.fn() } }))

const mockedApi = vi.mocked(api)
const existing = { id: 'old', project_id: 'p1', filename: 'dati.xlsx', file_type: 'xlsx', file_path: '', created_at: '' }

function renderUploader(onUpload = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><DocumentUploader projectId="p1" onUpload={onUpload} /></QueryClientProvider>)
}

describe('DocumentUploader', () => {
  beforeEach(() => vi.resetAllMocks())

  it('uploads a valid xlsx and reports success', async () => {
    mockedApi.get.mockResolvedValue([])
    mockedApi.postFile.mockResolvedValue({ id: 'new' })
    renderUploader()
    await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['xlsx'], 'dati.xlsx'))
    await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
    await waitFor(() => expect(mockedApi.postFile).toHaveBeenCalled())
    expect(await screen.findByText(/pronto per essere usato/i)).toBeInTheDocument()
  })

  it('shows the backend error for a corrupt xlsx', async () => {
    mockedApi.get.mockResolvedValue([])
    mockedApi.postFile.mockRejectedValue(new Error('Impossibile leggere il file Excel'))
    renderUploader()
    await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['bad'], 'rotto.xlsx'))
    await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Impossibile leggere il file Excel')
  })

  it('reconciles only a new ID after a lost upload response', async () => {
    mockedApi.get
      .mockResolvedValueOnce([existing]) // initial query
      .mockResolvedValueOnce([existing]) // baseline before POST
      .mockResolvedValueOnce([existing, { ...existing, id: 'new' }]) // reconciliation
      .mockResolvedValue([existing, { ...existing, id: 'new' }])
    mockedApi.postFile.mockRejectedValue(new Error('Network error'))
    renderUploader()
    await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['xlsx'], 'dati.xlsx'))
    await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
    expect(await screen.findByText(/caricato correttamente/i)).toBeInTheDocument()
  })

  it('rejects oversize files before calling the API', async () => {
    mockedApi.get.mockResolvedValue([])
    renderUploader()
    const file = new File(['x'], 'grande.xlsx')
    Object.defineProperty(file, 'size', { value: 25 * 1024 * 1024 + 1 })
    fireEvent.change(screen.getByLabelText(/scegli dal computer/i), { target: { files: [file] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('25 MB')
    expect(mockedApi.postFile).not.toHaveBeenCalled()
  })
})
