import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExampleDetailPage from './ExampleDetailPage'

const api = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('@/api/client', () => ({ api }))
vi.mock('@/context/KeycloakContext', () => ({ useAuth: () => ({ authenticated: false, register: vi.fn() }) }))
vi.mock('@/components/SchemaDiagram', () => ({ default: () => <div>diagramma</div> }))

const detail = {
  name: 'university', title: 'Università: studenti e corsi', subtitle: '', icon: 'school', tables: 2, relationships: 1,
  intro: ['Una segreteria ha un solo foglio.'], choices: ['Studenti e corsi diventano tabelle.'], notes: ['È l\'esempio più piccolo.'],
  prompt: 'Design a fully normalized relational schema',
  schema: {
    tables: [
      { name: 'students', description: 'Studenti', columns: [{ name: 'student_id', data_type: 'INTEGER', is_primary_key: true }] },
      { name: 'courses', description: 'Corsi', columns: [{ name: 'course_id', data_type: 'INTEGER', is_primary_key: true }] },
    ],
    relationships: [],
  },
  sources: [{ name: 'enrollments.csv', size: 2048, kind: 'csv' }],
  data: [
    { table: 'students', columns: ['student_id', 'name'], rows: [[1, 'Anna']], total: 30 },
    { table: 'courses', columns: ['course_id', 'title'], rows: [[1, 'Basi di dati']], total: 8 },
  ],
}

const renderPage = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={['/app/examples/university']}>
      <Routes><Route path="/app/examples/:name" element={<ExampleDetailPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => { api.get.mockReset() })

describe('ExampleDetailPage', () => {
  it('mostra documenti, richiesta, schema e dati con anteprima', async () => {
    api.get.mockResolvedValue(detail)
    renderPage()
    expect(await screen.findByText('Università: studenti e corsi')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/examples/university')
    const file = screen.getByRole('link', { name: /enrollments\.csv/ })
    expect(file).toHaveAttribute('href', '/api/examples/university/files/enrollments.csv')
    expect(screen.getByText(/Design a fully normalized/)).toBeInTheDocument()
    expect(await screen.findByText('diagramma')).toBeInTheDocument()
    expect(screen.getByText('Anna')).toBeInTheDocument()
    expect(screen.getByText(/Prime 1 righe su 30/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'courses' }))
    expect(screen.getByText('Basi di dati')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crea un account/i })).toBeInTheDocument()
  })

  it('mostra un messaggio se l\'esempio non esiste', async () => {
    api.get.mockImplementation(() => Promise.reject(new Error('404')))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/non esiste/i)
  })
})
