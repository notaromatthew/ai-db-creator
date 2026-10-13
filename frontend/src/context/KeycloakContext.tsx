import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import Keycloak from 'keycloak-js'
import { useNavigate } from 'react-router-dom'
import { api, SESSION_EXPIRED_EVENT } from '../api/client'
import { useConfig } from '../config/AppConfig'
import SiteFooter from '../brand/SiteFooter'
import { clearAutoLogin, currentPath, saveReturnTo, takeReturnTo } from '../hooks/authReturn'

interface AuthContextType {
  authenticated: boolean
  token: string | null
  username: string
  login: () => void
  register: () => void
  logout: () => void
  roles: string[]
  isAdmin: boolean
  keycloak: Keycloak | null
  initialized: boolean
  /** Il token non si e' potuto rinnovare: serve rientrare (la pagina resta, nulla si perde). */
  sessionExpired: boolean
}

const KeycloakContext = createContext<AuthContextType>({
  authenticated: false,
  token: null,
  username: 'Ospite',
  login: () => {},
  register: () => {},
  logout: () => {},
  roles: [],
  isAdmin: false,
  keycloak: null,
  initialized: false,
  sessionExpired: false,
})

let keycloakInstance: Keycloak | null = null
const getKeycloak = (url: string, realm: string, clientId: string) => {
  if (!keycloakInstance) keycloakInstance = new Keycloak({ url, realm, clientId })
  return keycloakInstance
}

export const KeycloakProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { config, loaded } = useConfig()
  const [roles, setRoles] = useState<string[]>([])
  const isRun = useRef(false)
  const [authenticated, setAuthenticated] = useState<boolean>(false)
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string>('Ospite')
  const [initialized, setInitialized] = useState<boolean>(false)
  const [sessionExpired, setSessionExpired] = useState<boolean>(false)
  const navigate = useNavigate()
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const syncAuthState = (auth: boolean) => {
    const keycloakInstance = getKeycloak(config.keycloak_url, config.keycloak_realm, config.keycloak_client_id)
    setAuthenticated(auth)
    if (auth) setSessionExpired(false)
    if (auth && keycloakInstance.token) {
      const activeToken = keycloakInstance.token
      setToken(activeToken)
      api.setToken(activeToken)
      const parsedUser =
        keycloakInstance.tokenParsed?.preferred_username ||
        keycloakInstance.tokenParsed?.sub ||
        'Utente Keycloak'
      setUsername(parsedUser)
      setRoles((keycloakInstance.tokenParsed as any)?.realm_access?.roles ?? [])
    } else {
      setRoles([])
      setToken(null)
      api.setToken(null)
      setUsername('Ospite')
    }
  }

  useEffect(() => {
    if (!loaded || isRun.current) return
    isRun.current = true
    const keycloakInstance = getKeycloak(config.keycloak_url, config.keycloak_realm, config.keycloak_client_id)

    // Set Keycloak Event Listeners
    keycloakInstance.onAuthSuccess = () => syncAuthState(true)
    keycloakInstance.onAuthLogout = () => syncAuthState(false)
    keycloakInstance.onTokenExpired = () => {
      keycloakInstance
        .updateToken(30)
        .then((refreshed) => {
          if (refreshed && keycloakInstance.token) {
            syncAuthState(true)
          }
        })
        .catch(() => {
          // Il rinnovo silenzioso non e' riuscito: niente blocchi, un avviso invita a rientrare.
          console.warn('Keycloak token refresh failed. User needs re-login.')
          setSessionExpired(true)
        })
    }

    api.setTokenRefresher(async () => {
      try {
        await keycloakInstance.updateToken(-1)
        syncAuthState(true)
        return keycloakInstance.token ?? null
      } catch {
        return null
      }
    })

    keycloakInstance
      .init({
        onLoad: 'check-sso',
        pkceMethod: 'S256',
        checkLoginIframe: false,
      })
      .then((auth) => {
        syncAuthState(auth)
        setInitialized(true)
        if (auth) {
          clearAutoLogin()
          // dopo il login si torna alla pagina da cui si era partiti
          const back = takeReturnTo()
          if (back) navigate(back, { replace: true })
        }
        // /app?register=1 arriva dai bottoni "Registrati" della landing
        if (!auth && new URLSearchParams(window.location.search).get('register') === '1') {
          saveReturnTo()
          keycloakInstance.register({ redirectUri: window.location.origin + '/app' })
        }

        // Periodic background token refresh every 30 seconds
        timer.current = setInterval(() => {
          if (keycloakInstance.authenticated) {
            keycloakInstance
              .updateToken(70)
              .then((refreshed) => {
                if (refreshed && keycloakInstance.token) {
                  syncAuthState(true)
                }
              })
              .catch((err) => {
                console.warn('Background token update warning:', err)
                if (keycloakInstance.isTokenExpired()) setSessionExpired(true)
              })
          }
        }, 30000)
      })
      .catch((err) => {
        console.error('Inizializzazione Keycloak fallita:', err)
        syncAuthState(false)
        setInitialized(true)
      })
    return () => {
      if (timer.current) clearInterval(timer.current)
    }
  }, [loaded])

  useEffect(() => {
    const onExpired = () => setSessionExpired(true)
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  const kc = () => getKeycloak(config.keycloak_url, config.keycloak_realm, config.keycloak_client_id)
  // Il percorso corrente (con i parametri) si salva in sessione e si riapre dopo l'accesso.
  const login = () => {
    saveReturnTo(currentPath())
    kc().login({ redirectUri: window.location.origin + '/app' })
  }

  const register = () => {
    saveReturnTo(currentPath())
    kc().register({ redirectUri: window.location.origin + '/app' })
  }

  const logout = () => {
    kc().logout({ redirectUri: window.location.origin + '/' })
  }

  if (!initialized) {
    return (
      <div className="flex min-h-screen w-screen flex-col bg-tecnia-bg text-tecnia-ink">
        <div className="flex flex-1 items-center justify-center" role="status">
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-orange-500 border-t-transparent" aria-hidden="true"></div>
            <p className="text-sm font-semibold text-tecnia-muted">Accesso in corso…</p>
          </div>
        </div>
        <SiteFooter />
      </div>
    )
  }

  return (
    <KeycloakContext.Provider
      value={{
        authenticated,
        token,
        username,
        login,
        register,
        logout,
        roles,
        isAdmin: roles.includes('aidb-admin'),
        keycloak: keycloakInstance,
        initialized,
        sessionExpired,
      }}
    >
      {children}
    </KeycloakContext.Provider>
  )
}

export const useAuth = () => useContext(KeycloakContext)
