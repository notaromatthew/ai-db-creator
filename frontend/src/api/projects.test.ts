import { beforeEach, describe, expect, it, vi } from 'vitest'
import { cancelJob, createJob, listJobs, listQueries, setProjectDialect } from './projects'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }))
vi.mock('./client', () => ({ api }))

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('api/projects', () => {
  it('chiama le rotte dei lavori', async () => {
    api.post.mockResolvedValue({ id: 'j' })
    api.get.mockResolvedValue({ jobs: [{ id: 'j' }] })
    await createJob('p', { kind: 'schema', prompt: 'x' })
    expect(api.post).toHaveBeenCalledWith('/projects/p/jobs', { kind: 'schema', prompt: 'x' })
    expect(await listJobs('p', 'running')).toEqual([{ id: 'j' }])
    expect(api.get).toHaveBeenCalledWith('/projects/p/jobs?status=running')
    await cancelJob('p', 'j')
    expect(api.post).toHaveBeenCalledWith('/projects/p/jobs/j/cancel', {})
  })
  it('gestisce cronologia query e dialetto', async () => {
    api.get.mockResolvedValue({})
    expect(await listQueries('p')).toEqual([])
    api.put.mockResolvedValue({ target_dialect: 'oracle' })
    await setProjectDialect('p', 'oracle')
    expect(api.put).toHaveBeenCalledWith('/projects/p/dialect', { dialect: 'oracle' })
  })
})
