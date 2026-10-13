import React, { createContext, useContext, useEffect, useState } from 'react'

export interface PublicConfig {
  research_mode: boolean
  auth_enabled: boolean
  keycloak_url: string
  keycloak_realm: string
  keycloak_client_id: string
  registration_open: boolean
  maintenance_message: string
}

const fallback: PublicConfig = {
  research_mode: false,
  auth_enabled: true,
  keycloak_url: import.meta.env.VITE_KEYCLOAK_URL || '',
  keycloak_realm: import.meta.env.VITE_KEYCLOAK_REALM || 'aidbcreator',
  keycloak_client_id: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'aidbcreator-app',
  registration_open: true,
  maintenance_message: '',
}

const ConfigContext = createContext<{ config: PublicConfig; loaded: boolean }>({ config: fallback, loaded: false })

const apiBase = () => import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? window.location.origin : '')

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<PublicConfig>(fallback)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let alive = true
    fetch(apiBase() + '/api/config')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((c) => alive && setConfig({ ...fallback, ...c }))
      .catch(() => {})
      .finally(() => alive && setLoaded(true))
    return () => { alive = false }
  }, [])

  return <ConfigContext.Provider value={{ config, loaded }}>{children}</ConfigContext.Provider>
}

export const useConfig = () => useContext(ConfigContext)
