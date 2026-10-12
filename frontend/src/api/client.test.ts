import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClient } from './client'

describe('ApiClient multipart uploads', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('passes an existing FormData unchanged for SQL import', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ tables: 1 }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const form = new FormData()
    form.append('file', new File(['CREATE TABLE t (id INTEGER);'], 'schema.sql'))
    await new ApiClient('http://test').postFile('/projects/p1/import-sql', form)
    expect(fetchMock.mock.calls[0][1].body).toBe(form)
    expect(Array.from(form.keys())).toEqual(['file'])
  })
})

describe('ApiClient auth header', () => {
  afterEach(() => vi.unstubAllGlobals())
  const ok = () => new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } })

  it('omits Authorization without token and sends Bearer with token', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(ok()))
    vi.stubGlobal('fetch', fetchMock)
    const c = new ApiClient('http://test')
    await c.get('/x')
    expect(fetchMock.mock.calls[0][0]).toBe('http://test/api/x')
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined()
    c.setToken('abc')
    await c.get('/x')
    await c.post('/x', { a: 1 })
    await c.put('/x', {})
    await c.delete('/x')
    await c.postFile('/x', new FormData())
    for (const call of fetchMock.mock.calls.slice(1)) {
      expect(call[1].headers.Authorization).toBe('Bearer abc')
    }
    expect(fetchMock.mock.calls[2][1].headers['Content-Type']).toBe('application/json')
    c.setToken(null)
    await c.get('/x')
    expect(fetchMock.mock.calls[6][1].headers.Authorization).toBeUndefined()
  })

  it('throws backend detail on error responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'nope' }), { status: 400, headers: { 'content-type': 'application/json' } })))
    await expect(new ApiClient('http://test').get('/x')).rejects.toThrow('nope')
  })

  it('defaults base to window origin', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(ok()))
    vi.stubGlobal('fetch', fetchMock)
    await new ApiClient().get('/x')
    expect(fetchMock.mock.calls[0][0]).toBe(window.location.origin + '/api/x')
  })
})
