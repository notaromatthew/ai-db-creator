import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import Keycloak from 'keycloak-js'
import { api } from '../api/client'
import { useConfig } from '../config/AppConfig'

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

  const syncAuthState = (auth: boolean) => {
    const keycloakInstance = getKeycloak(config.keycloak_url, config.keycloak_realm, config.keycloak_client_id)
    setAuthenticated(auth)
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
          console.warn('Keycloak token refresh failed. User needs re-login.')
          syncAuthState(false)
        })
    }

    keycloakInstance
      .init({
        onLoad: 'check-sso',
        pkceMethod: 'S256',
        checkLoginIframe: false,
      })
      .then((auth) => {
        syncAuthState(auth)
        setInitialized(true)

        // Periodic background token refresh every 30 seconds
        setInterval(() => {
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
              })
          }
        }, 30000)
      })
      .catch((err) => {
        console.error('Inizializzazione Keycloak fallita:', err)
        syncAuthState(false)
        setInitialized(true)
      })
  }, [loaded])

  const kc = () => getKeycloak(config.keycloak_url, config.keycloak_realm, config.keycloak_client_id)
  const login = () => {
    kc().login({ redirectUri: window.location.origin + '/app' })
  }

  const register = () => {
    kc().register({ redirectUri: window.location.origin + '/app' })
  }

  const logout = () => {
    kc().logout({ redirectUri: window.location.origin + '/' })
  }

  if (!initialized) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-tecnia-bg text-tecnia-ink">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-orange-500 border-t-transparent"></div>
          <p className="text-sm font-semibold text-tecnia-muted">Accesso in corso…</p>
        </div>
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
      }}
    >
      {children}
    </KeycloakContext.Provider>
  )
}

export const useAuth = () => useContext(KeycloakContext)
