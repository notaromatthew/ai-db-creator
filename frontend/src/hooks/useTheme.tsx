import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const KEY = 'theme'

interface ThemeValue { dark: boolean; toggle: () => void }
const ThemeContext = createContext<ThemeValue>({ dark: false, toggle: () => {} })

function readInitial(): boolean {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'dark') return true
    if (saved === 'light') return false
  } catch { /* storage non disponibile: si usa la preferenza del sistema */ }
  try {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  } catch {
    return false
  }
}

/** Tema chiaro/scuro: ricorda la scelta della persona e altrimenti segue il sistema. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [dark, setDark] = useState(readInitial)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  const toggle = useCallback(() => {
    setDark((current) => {
      try { localStorage.setItem(KEY, current ? 'light' : 'dark') } catch { /* la scelta vale solo per questa visita */ }
      return !current
    })
  }, [])

  const value = useMemo(() => ({ dark, toggle }), [dark, toggle])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)
