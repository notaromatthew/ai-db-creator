import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Landing from './Landing'

describe('Landing', () => {
  it('renders Italian with links to /app', () => {
    render(<Landing lang="it" />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/pronto da usare/i)
    expect(document.documentElement.lang).toBe('it')
    expect(screen.getAllByRole('link', { name: /accedi/i }).some((a) => a.getAttribute('href') === '/app')).toBe(true)
    expect(screen.getAllByRole('link', { name: /registrati|crea un account/i }).some((a) => a.getAttribute('href') === '/app?register=1')).toBe(true)
    expect(screen.getByRole('link', { name: 'Guida' })).toHaveAttribute('href', '/app/help')
    expect(screen.queryByText(/vedi i benchmark/i)).toBeNull()
  })
  it('renders English', () => {
    render(<Landing lang="en" />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/ready to use/i)
    expect(document.documentElement.lang).toBe('en')
    expect(document.title).toMatch(/From your documents/)
    expect(screen.getAllByRole('link', { name: /log in/i })[0]).toHaveAttribute('href', '/app')
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument()
  })
})
