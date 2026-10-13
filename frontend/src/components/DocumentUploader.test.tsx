import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DocumentUploader, { RETRY_DELAYS_MS } from './DocumentUploader'
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

  describe('coda, stato per file e riprova', () => {
    const transient = () => Object.assign(new Error('Servizio non disponibile'), { status: 503 })
    beforeEach(() => { RETRY_DELAYS_MS.splice(0, RETRY_DELAYS_MS.length, 1, 1, 1) })

    it('ritenta da solo gli errori temporanei e poi carica il file', async () => {
      mockedApi.get.mockResolvedValue([])
      mockedApi.postFile.mockRejectedValueOnce(transient()).mockRejectedValueOnce(transient()).mockResolvedValue({ id: 'n' })
      renderUploader()
      await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['x'], 'dati.csv'))
      expect(screen.getByText(/in coda/i)).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
      expect(await screen.findByText(/pronto per essere usato/i)).toBeInTheDocument()
      expect(mockedApi.postFile).toHaveBeenCalledTimes(3)
      expect(screen.getByText(/Caricato/)).toBeInTheDocument()
    })

    it('dopo 3 tentativi falliti mostra l\'errore e il pulsante Riprova', async () => {
      mockedApi.get.mockResolvedValue([])
      mockedApi.postFile.mockRejectedValue(transient())
      renderUploader()
      await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['x'], 'dati.csv'))
      await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
      const retry = await screen.findByRole('button', { name: /riprova a caricare dati.csv/i })
      expect(mockedApi.postFile).toHaveBeenCalledTimes(4)
      mockedApi.postFile.mockReset().mockResolvedValue({ id: 'n' })
      await userEvent.click(retry)
      expect(await screen.findByText(/pronto per essere usato/i)).toBeInTheDocument()
    })

    it('non ritenta gli errori di validazione (4xx)', async () => {
      mockedApi.get.mockResolvedValue([])
      mockedApi.postFile.mockRejectedValue(Object.assign(new Error('File vuoto'), { status: 422 }))
      renderUploader()
      await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), new File(['x'], 'vuoto.csv'))
      await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
      expect(await screen.findByRole('alert')).toHaveTextContent('File vuoto')
      expect(mockedApi.postFile).toHaveBeenCalledTimes(1)
    })

    it('carica più file uno alla volta: un errore non ferma gli altri', async () => {
      mockedApi.get.mockResolvedValue([])
      mockedApi.postFile.mockRejectedValueOnce(Object.assign(new Error('Illeggibile'), { status: 400 })).mockResolvedValue({ id: 'n' })
      renderUploader()
      await userEvent.upload(screen.getByLabelText(/scegli dal computer/i), [new File(['a'], 'a.csv'), new File(['b'], 'b.csv')])
      expect(screen.getAllByText(/in coda/i)).toHaveLength(2)
      await userEvent.click(screen.getByRole('button', { name: /carica file/i }))
      expect(await screen.findByText(/“b.csv” è pronto/i)).toBeInTheDocument()
      expect(mockedApi.postFile).toHaveBeenCalledTimes(2)
      expect(screen.getByRole('button', { name: /riprova a caricare a.csv/i })).toBeInTheDocument()
    })
  })
})
