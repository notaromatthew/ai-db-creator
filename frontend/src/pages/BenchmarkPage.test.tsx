import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import BenchmarkPage from './BenchmarkPage'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

const benchmarkResult = {
  id: 'benchmark-1',
  scenario: 'E-Commerce System',
  provider: 'ollama',
  model: 'gemma2:9b',
  norm3_score: 100,
  relationship_f1: 0.8,
  schema_quality_heuristic_estimate: 1,
  data_metric_label: 'Schema-derived heuristic (not an RQ2 population measure)',
  latency_seconds: 1.25,
}

describe('BenchmarkPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path === '/benchmark/scenarios') {
        return [{ key: 'ecommerce', title: 'E-Commerce System' }]
      }
      if (path === '/benchmark/results') {
        return { results: [benchmarkResult], votes: [] }
      }
      if (path === '/settings/ollama-models') {
        return { models: ['gemma2:9b'] }
      }
      return { status: 'idle', progress: 0, message: '', etc_seconds: null }
    })
  })

  it('shows persisted output after a successful benchmark run', async () => {
    vi.mocked(api.post).mockResolvedValue(benchmarkResult)
    render(<BenchmarkPage />)

    await userEvent.click(await screen.findByRole('button', { name: /Avvia Test Benchmark/ }))

    expect(api.post).toHaveBeenCalledWith('/benchmark/run', {
      scenario: 'ecommerce',
      temperature: 0.1,
      provider: 'ollama',
      model: 'gemma2:9b',
    })
    expect(await screen.findByText(/completato in 1.25s/)).toBeInTheDocument()
    expect((await screen.findAllByText('E-Commerce System')).length).toBeGreaterThanOrEqual(2)
  })
})
