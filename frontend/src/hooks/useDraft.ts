import { useCallback, useEffect, useRef, useState } from 'react'

const PREFIX = 'aidb.draft.'

const read = <T,>(key: string, initial: T): T => {
  try {
    const raw = sessionStorage.getItem(PREFIX + key)
    return raw === null ? initial : (JSON.parse(raw) as T)
  } catch {
    return initial
  }
}

export function clearDraft(key: string) {
  try { sessionStorage.removeItem(PREFIX + key) } catch { /* niente da cancellare */ }
}

/**
 * Come useState, ma il valore in compilazione si salva in sessione: se la sessione
 * scade e si passa dal login, i campi ricompaiono al ritorno sulla stessa pagina.
 * Con `initial` uguale al valore, la bozza viene rimossa (nessun residuo).
 */
export function useDraft<T>(key: string, initial: T): [T, (value: T) => void, () => void] {
  const [value, setValue] = useState<T>(() => read(key, initial))
  const initialRef = useRef(initial)

  useEffect(() => {
    try {
      if (JSON.stringify(value) === JSON.stringify(initialRef.current)) sessionStorage.removeItem(PREFIX + key)
      else sessionStorage.setItem(PREFIX + key, JSON.stringify(value))
    } catch { /* storage pieno o bloccato: la bozza resta solo in memoria */ }
  }, [key, value])

  const clear = useCallback(() => {
    clearDraft(key)
    setValue(initialRef.current)
  }, [key])

  return [value, setValue, clear]
}
