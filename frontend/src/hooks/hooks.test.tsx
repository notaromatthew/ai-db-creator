import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useDraft } from './useDraft'
import { ThemeProvider, useTheme } from './useTheme'
import { markAutoLogin, sanitizeReturnPath, saveReturnTo, shouldAutoLogin, takeReturnTo } from './authReturn'

beforeEach(() => { sessionStorage.clear(); localStorage.clear(); document.documentElement.classList.remove('dark') })

describe('useDraft', () => {
  it('salva il valore in sessione e lo ripropone al ritorno', () => {
    const first = renderHook(() => useDraft('k', ''))
    act(() => first.result.current[1]('ciao'))
    first.unmount()
    const second = renderHook(() => useDraft('k', ''))
    expect(second.result.current[0]).toBe('ciao')
    act(() => second.result.current[2]())
    expect(second.result.current[0]).toBe('')
    expect(sessionStorage.getItem('aidb.draft.k')).toBeNull()
  })
})

describe('authReturn', () => {
  it('conserva percorso e parametri, ma solo interni a /app', () => {
    saveReturnTo('/app/projects/42?tab=schema')
    expect(takeReturnTo()).toBe('/app/projects/42?tab=schema')
    expect(takeReturnTo()).toBeNull()
    expect(sanitizeReturnPath('https://evil.example/app')).toBeNull()
    expect(sanitizeReturnPath('//evil.example')).toBeNull()
    expect(sanitizeReturnPath('/app/login')).toBeNull()
    expect(sanitizeReturnPath('/app/help?register=1')).toBe('/app/help')
  })
  it('il reindirizzamento automatico parte una volta sola', () => {
    expect(shouldAutoLogin()).toBe(true)
    markAutoLogin()
    expect(shouldAutoLogin()).toBe(false)
  })
})

describe('useTheme', () => {
  it('ricorda la scelta e applica la classe dark', () => {
    const { result } = renderHook(() => useTheme(), { wrapper: ThemeProvider })
    expect(result.current.dark).toBe(false)
    act(() => result.current.toggle())
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
    const again = renderHook(() => useTheme(), { wrapper: ThemeProvider })
    expect(again.result.current.dark).toBe(true)
    act(() => again.result.current.toggle())
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
