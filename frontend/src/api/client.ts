import { QueryClient } from '@tanstack/react-query'

const getApiBase = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin
  }
  return 'http://localhost:8000'
}

/** Eventi sulla finestra: la barra di stato dell'app li ascolta per avvisare con calma. */
export const SESSION_EXPIRED_EVENT = 'aidb:session-expired'
export const NETWORK_DOWN_EVENT = 'aidb:network-down'
export const NETWORK_UP_EVENT = 'aidb:network-up'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Errori che ha senso ritentare da soli: rete assente, server in difficolta', troppe richieste. */
export const isRetryable = (e: unknown) => {
  const status = (e as { status?: number } | null)?.status
  return status === 0 || status === 408 || status === 429 || (typeof status === 'number' && status >= 500)
}

const FRIENDLY: Record<number, string> = {
  401: 'La sessione è scaduta: rientra per continuare. Quello che stavi scrivendo resta salvato.',
  403: 'Non hai il permesso per farlo. Chiedi al proprietario del progetto di darti l\'accesso.',
  404: 'Non troviamo quello che cerchi: potrebbe essere stato rimosso.',
  413: 'Il file è troppo grande. Scegline uno più piccolo.',
  429: 'Hai fatto molte richieste ravvicinate. Aspetta un momento e riprova.',
  500: 'Il servizio ha un problema momentaneo. Riprova fra qualche istante.',
}
const friendly = (status: number) => FRIENDLY[status] ?? (status >= 500 ? FRIENDLY[500] : '')
const OFFLINE_MESSAGE = 'Connessione assente: controlla la rete. Riproviamo in automatico.'

const emit = (name: string) => {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(name))
}
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export class ApiClient {
  private base: string
  private token: string | null = null
  private refresher: (() => Promise<string | null>) | null = null
  private refreshing: Promise<string | null> | null = null
  private down = false
  /** Pause tra i tentativi sulle richieste di sola lettura quando la rete cade. */
  retryDelays = [600, 1800]

  constructor(base?: string) {
    this.base = base || getApiBase()
  }

  setToken(token: string | null) {
    this.token = token
  }

  /** Funzione che rinnova il token (Keycloak) e restituisce quello nuovo, o null se non riesce. */
  setTokenRefresher(fn: (() => Promise<string | null>) | null) {
    this.refresher = fn
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

  private async fetchOnce(path: string, build: () => RequestInit, idempotent: boolean): Promise<Response> {
    for (let attempt = 0; ; attempt++) {
      try {
        const res = await fetch(this.url(path), build())
        if (this.down) { this.down = false; emit(NETWORK_UP_EVENT) }
        return res
      } catch (e) {
        if (!this.down) { this.down = true; emit(NETWORK_DOWN_EVENT) }
        if (!idempotent || attempt >= this.retryDelays.length) throw new ApiError(OFFLINE_MESSAGE, 0)
        await sleep(this.retryDelays[attempt])
      }
    }
  }

  private refreshOnce(): Promise<string | null> {
    if (!this.refresher) return Promise.resolve(null)
    if (!this.refreshing) {
      this.refreshing = this.refresher().catch(() => null).finally(() => { this.refreshing = null })
    }
    return this.refreshing
  }

  /** Esegue la richiesta; su 401 prova un solo rinnovo del token e ripete la richiesta una volta. */
  private async send(path: string, build: () => RequestInit, idempotent = false): Promise<Response> {
    let res = await this.fetchOnce(path, build, idempotent)
    if (res.status === 401 && this.token) {
      const fresh = await this.refreshOnce()
      if (fresh) {
        this.token = fresh
        res = await this.fetchOnce(path, build, idempotent)
      }
      if (res.status === 401) emit(SESSION_EXPIRED_EVENT)
    }
    await this._checkError(res)
    return res
  }

  async get(path: string) {
    const res = await this.send(path, () => ({ headers: this.headers() }), true)
    return res.json()
  }

  async post(path: string, data: any) {
    const res = await this.send(path, () => ({
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }))
    return res.json()
  }

  async delete(path: string, data?: any) {
    const res = await this.send(path, () => {
      const opts: RequestInit = {
        method: 'DELETE',
        headers: this.headers(data ? { 'Content-Type': 'application/json' } : {}),
      }
      if (data) opts.body = JSON.stringify(data)
      return opts
    })
    return res.json()
  }

  async put(path: string, data: any) {
    const res = await this.send(path, () => ({
      method: 'PUT',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }))
    return res.json()
  }

  async postFile(path: string, file: File | FormData) {
    const formData = file instanceof FormData ? file : new FormData()
    if (file instanceof File) formData.append('file', file)
    const res = await this.send(path, () => ({
      method: 'POST',
      headers: this.headers(),
      body: formData,
    }))
    const contentType = res.headers.get('content-type') || ''
    return contentType.includes('application/json') ? res.json() : null
  }

  async _checkError(res: Response) {
    if (res.ok) return
    let msg = ''
    try {
      const ct = res.headers.get('content-type') || ''
      if (ct.includes('application/json')) {
        const body = await res.json()
        if (body.detail) {
          msg = Array.isArray(body.detail)
            ? body.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
            : String(body.detail)
        }
      } else {
        const text = await res.text()
        // una pagina HTML d'errore (proxy, 502) non e' un messaggio per le persone
        if (text && text.length < 300 && !/<\w+/.test(text)) msg = text
      }
    } catch {}
    throw new ApiError(msg || friendly(res.status) || res.statusText || 'Qualcosa è andato storto. Riprova.', res.status)
  }
}

export const api = new ApiClient()
