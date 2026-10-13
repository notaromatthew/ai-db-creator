import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ThemeProvider } from './hooks/useTheme'
import { api } from './api/client'

const kc = vi.hoisted(() => ({ login: vi.fn(), register: vi.fn() }))
vi.mock('keycloak-js', () => ({
  default: class {
    authenticated = false
    token = undefined
    init = vi.fn().mockResolvedValue(false)
    login = kc.login
    register = kc.register
    logout = vi.fn()
    isTokenExpired = () => false
    updateToken = vi.fn().mockRejectedValue(new Error('no'))
  },
}))

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BrowserRouter><ThemeProvider><App /></ThemeProvider></BrowserRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  sessionStorage.clear(); localStorage.clear()
  kc.login.mockClear(); kc.register.mockClear()
  api.retryDelays = []
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
})
afterEach(() => vi.unstubAllGlobals())

describe('footer con i dati di TecnIA', () => {
  it.each(['/app', '/app/help', '/app/privacy', '/app/cookie', '/app/login'])('compare su %s', async (path) => {
    renderAt(path)
    const footer = await screen.findByRole('contentinfo')
    expect(footer).toHaveTextContent('04941440168')
    expect(footer).toHaveTextContent(`© ${new Date().getFullYear()}`)
    expect(screen.getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/app/privacy')
    expect(screen.getByRole('link', { name: 'Cookie' })).toHaveAttribute('href', '/app/cookie')
    expect(screen.getByRole('link', { name: 'Contatti' })).toHaveAttribute('href', expect.stringContaining('tecniaweb.it'))
  })
})

describe('accesso', () => {
  it('/app/login apre subito Keycloak', async () => {
    renderAt('/app/login')
    await waitFor(() => expect(kc.login).toHaveBeenCalledTimes(1))
  })

  it('/app/register apre subito la registrazione', async () => {
    renderAt('/app/register')
    await waitFor(() => expect(kc.register).toHaveBeenCalledTimes(1))
  })

  it('entrando in una pagina protetta senza sessione si va al login e si ricorda la pagina', async () => {
    renderAt('/app/projects/abc?tab=schema')
    await waitFor(() => expect(kc.login).toHaveBeenCalledTimes(1))
    expect(sessionStorage.getItem('aidb.returnTo')).toBe('/app/projects/abc?tab=schema')
  })

  it('?register=1 dalla landing apre la registrazione', async () => {
    renderAt('/app?register=1')
    await waitFor(() => expect(kc.register).toHaveBeenCalled())
  })
})

describe('accessibilità di base', () => {
  it('ha il salto al contenuto, il menu etichettato e la pagina legale con il segnaposto', async () => {
    renderAt('/app/privacy')
    expect(await screen.findByRole('link', { name: 'Vai al contenuto' })).toHaveAttribute('href', '#contenuto')
    expect(screen.getByRole('navigation', { name: 'Navigazione principale' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: /privacy/i })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/da fornire da TecnIA/i)
  })
})
