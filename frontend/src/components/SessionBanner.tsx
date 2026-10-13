import { useEffect, useState } from 'react'
import { NETWORK_DOWN_EVENT, NETWORK_UP_EVENT } from '@/api/client'
import { useAuth } from '@/context/KeycloakContext'

/** Avvisi non bloccanti: connessione assente e sessione scaduta. L'area e' una regione aria-live. */
export default function SessionBanner() {
  const { sessionExpired, login } = useAuth()
  const [offline, setOffline] = useState(() => typeof navigator !== 'undefined' && navigator.onLine === false)

  useEffect(() => {
    const down = () => setOffline(true)
    const up = () => setOffline(false)
    window.addEventListener('offline', down)
    window.addEventListener('online', up)
    window.addEventListener(NETWORK_DOWN_EVENT, down)
    window.addEventListener(NETWORK_UP_EVENT, up)
    return () => {
      window.removeEventListener('offline', down)
      window.removeEventListener('online', up)
      window.removeEventListener(NETWORK_DOWN_EVENT, down)
      window.removeEventListener(NETWORK_UP_EVENT, up)
    }
  }, [])

  return (
    <div role="status" aria-live="polite" className="relative z-10">
      {offline && (
        <p className="flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-900 dark:bg-amber-950 dark:text-amber-100">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">wifi_off</span>
          Connessione assente, riprovo. Quello che hai scritto resta qui.
        </p>
      )}
      {sessionExpired && (
        <p className="flex flex-wrap items-center justify-center gap-3 bg-red-100 px-4 py-2 text-center text-sm font-medium text-red-900 dark:bg-red-950 dark:text-red-100">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">lock_clock</span>
          Sessione scaduta, rientra per continuare: tornerai a questa pagina e i campi in compilazione saranno ancora lì.
          <button type="button" onClick={login} className="secondary-button !min-h-8 !px-4">Rientra</button>
        </p>
      )}
    </div>
  )
}
