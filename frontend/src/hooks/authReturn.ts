// Ricorda dove si trovava la persona prima del login, per riportarla alla stessa pagina.
const RETURN_KEY = 'aidb.returnTo'
const AUTO_KEY = 'aidb.autoLoginAt'

/** Accetta solo percorsi interni sotto /app (mai indirizzi esterni) e toglie i parametri di accesso. */
export function sanitizeReturnPath(path: string | null | undefined): string | null {
  if (!path || !path.startsWith('/app') || path.startsWith('//')) return null
  const url = new URL(path, 'http://x')
  if (/^\/app\/(login|register)\/?$/.test(url.pathname)) return null
  url.searchParams.delete('register')
  const out = url.pathname + url.search + url.hash
  return out === '/app' ? null : out
}

export function currentPath(): string {
  return window.location.pathname + window.location.search + window.location.hash
}

export function saveReturnTo(path: string | null = currentPath()) {
  const safe = sanitizeReturnPath(path)
  try {
    if (safe) sessionStorage.setItem(RETURN_KEY, safe)
  } catch { /* senza storage si torna alla home dell'app */ }
}

export function takeReturnTo(): string | null {
  try {
    const value = sanitizeReturnPath(sessionStorage.getItem(RETURN_KEY))
    sessionStorage.removeItem(RETURN_KEY)
    return value
  } catch {
    return null
  }
}

/** Evita il giro infinito: il reindirizzamento automatico al login parte una sola volta per scheda. */
export function shouldAutoLogin(): boolean {
  try { return sessionStorage.getItem(AUTO_KEY) === null } catch { return true }
}
export function markAutoLogin() {
  try { sessionStorage.setItem(AUTO_KEY, String(Date.now())) } catch { /* ignora */ }
}
export function clearAutoLogin() {
  try { sessionStorage.removeItem(AUTO_KEY) } catch { /* ignora */ }
}
