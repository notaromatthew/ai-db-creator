import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import Keycloak from 'keycloak-js'
import { api } from '../api/client'

interface AuthContextType {
  authenticated: boolean
  token: string | null
  username: string
  login: () => void
  logout: () => void
  keycloak: Keycloak | null
  initialized: boolean
}

const KeycloakContext = createContext<AuthContextType>({
  authenticated: false,
  token: null,
  username: 'Ospite',
  login: () => {},
  logout: () => {},
  keycloak: null,
  initialized: false,
})

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080'
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'aidbcreator'
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'aidbcreator-app'

// Singleton Keycloak instance
const keycloakInstance = new Keycloak({
  url: KEYCLOAK_URL,
  realm: KEYCLOAK_REALM,
  clientId: KEYCLOAK_CLIENT_ID,
})

export const KeycloakProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isRun = useRef(false)
  const [authenticated, setAuthenticated] = useState<boolean>(false)
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string>('Ospite')
  const [initialized, setInitialized] = useState<boolean>(false)

  const syncAuthState = (auth: boolean) => {
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
    } else {
      setToken(null)
      api.setToken(null)
      setUsername('Ospite')
    }
  }

  useEffect(() => {
    if (isRun.current) return
    isRun.current = true

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
  }, [])

  const login = () => {
    keycloakInstance.login({ redirectUri: window.location.origin + '/' })
  }

  const logout = () => {
    keycloakInstance.logout({ redirectUri: window.location.origin + '/' })
  }

  if (!initialized) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
          <p className="text-sm font-semibold text-slate-400">Autenticazione Keycloak in corso...</p>
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
        logout,
        keycloak: keycloakInstance,
        initialized,
      }}
    >
      {children}
    </KeycloakContext.Provider>
  )
}

export const useAuth = () => useContext(KeycloakContext)
