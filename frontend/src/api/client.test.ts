import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, NETWORK_DOWN_EVENT, NETWORK_UP_EVENT, SESSION_EXPIRED_EVENT } from './client'

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

describe('ApiClient sessione e rete', () => {
  afterEach(() => vi.unstubAllGlobals())
  const json = (status: number, body: unknown = {}) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

  it('su 401 rinnova il token una volta sola e ripete la richiesta', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json(401, { detail: 'x' })).mockResolvedValueOnce(json(200, { ok: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    const c = new ApiClient('http://test')
    c.setToken('vecchio')
    const refresher = vi.fn().mockResolvedValue('nuovo')
    c.setTokenRefresher(refresher)
    await expect(c.post('/x', {})).resolves.toEqual({ ok: 1 })
    expect(refresher).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer nuovo')
  })

  it('se il rinnovo fallisce segnala la sessione scaduta con un messaggio chiaro', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(401, {})))
    const c = new ApiClient('http://test')
    c.setToken('vecchio')
    c.setTokenRefresher(vi.fn().mockResolvedValue(null))
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener)
    await expect(c.get('/x')).rejects.toThrow(/sessione è scaduta/i)
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('con la rete assente ritenta le letture e poi avvisa; al ritorno segnala la connessione', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('fail')).mockResolvedValueOnce(json(200, { ok: 1 }))
    vi.stubGlobal('fetch', fetchMock)
    const c = new ApiClient('http://test')
    c.retryDelays = [1, 1]
    const down = vi.fn(); const up = vi.fn()
    window.addEventListener(NETWORK_DOWN_EVENT, down); window.addEventListener(NETWORK_UP_EVENT, up)
    await expect(c.get('/x')).resolves.toEqual({ ok: 1 })
    expect(down).toHaveBeenCalledTimes(1); expect(up).toHaveBeenCalledTimes(1)

    fetchMock.mockRejectedValue(new TypeError('fail'))
    await expect(c.get('/x')).rejects.toMatchObject({ status: 0, message: expect.stringMatching(/connessione assente/i) })
    // le scritture non si ripetono da sole
    fetchMock.mockClear()
    await expect(c.post('/x', {})).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    window.removeEventListener(NETWORK_DOWN_EVENT, down); window.removeEventListener(NETWORK_UP_EVENT, up)
  })

  it('spiega cosa fare quando il server non da dettagli', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Bad Gateway</html>', { status: 502, headers: { 'content-type': 'text/html' } })))
    await expect(new ApiClient('http://test').post('/x', {})).rejects.toThrow(/riprova/i)
  })
})
