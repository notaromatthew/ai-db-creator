import { QueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiClient {
  private base: string
  private token: string | null = null

  constructor(base: string = API_BASE) {
    this.base = base
  }

  setToken(token: string | null) {
    this.token = token
  }

  private headers(custom: Record<string, string> = {}): Record<string, string> {
    const h: Record<string, string> = { ...custom }
    if (this.token) {
      h['Authorization'] = `Bearer ${this.token}`
    }
    return h
  }

  private url(path: string) {
    return this.base + '/api' + path
  }

  async get(path: string) {
    const res = await fetch(this.url(path), { headers: this.headers() })
    await this._checkError(res)
    return res.json()
  }

  async post(path: string, data: any) {
    const res = await fetch(this.url(path), {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    })
    await this._checkError(res)
    return res.json()
  }

  async delete(path: string, data?: any) {
    const opts: RequestInit = {
      method: 'DELETE',
      headers: this.headers(data ? { 'Content-Type': 'application/json' } : {}),
    }
    if (data) {
      opts.body = JSON.stringify(data)
    }
    const res = await fetch(this.url(path), opts)
    await this._checkError(res)
    return res.json()
  }

  async put(path: string, data: any) {
    const res = await fetch(this.url(path), {
      method: 'PUT',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    })
    await this._checkError(res)
    return res.json()
  }

  async postFile(path: string, file: File | FormData) {
    const formData = file instanceof FormData ? file : new FormData()
    if (file instanceof File) formData.append('file', file)
    const res = await fetch(this.url(path), {
      method: 'POST',
      headers: this.headers(),
      body: formData,
    })
    await this._checkError(res)
    const contentType = res.headers.get('content-type') || ''
    return contentType.includes('application/json') ? res.json() : null
  }


  async _checkError(res: Response) {
    if (res.ok) return
    let msg = res.statusText
    try {
      const ct = res.headers.get('content-type') || ''
      if (ct.includes('application/json')) {
        const body = await res.json()
        if (body.detail) {
          msg = Array.isArray(body.detail)
            ? body.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
            : body.detail
        }
      } else {
        msg = await res.text()
      }
    } catch {}
    throw new Error(msg)
  }
}

export const api = new ApiClient()
