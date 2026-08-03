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
