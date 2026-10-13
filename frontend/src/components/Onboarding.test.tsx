import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OnboardingDialog, hasSeenOnboarding, markOnboardingSeen } from './Onboarding'

beforeEach(() => localStorage.clear())

describe('Onboarding', () => {
  it('guida in tre schermate e si chiude alla fine', async () => {
    const onClose = vi.fn()
    render(<OnboardingDialog open onClose={onClose} />)
    expect(screen.getByRole('dialog', { name: /benvenuto/i })).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText('Passo 1 di 3')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Avanti' }))
    expect(screen.getByText('Passo 2 di 3')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Avanti' }))
    expect(screen.getByText('Passo 3 di 3')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Inizia' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('si può saltare e chiudere con Esc', async () => {
    const onClose = vi.fn()
    render(<OnboardingDialog open onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: /salta/i }))
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('ricorda per utente che è stato visto', () => {
    expect(hasSeenOnboarding('ada')).toBe(false)
    markOnboardingSeen('ada')
    expect(hasSeenOnboarding('ada')).toBe(true)
    expect(hasSeenOnboarding('bob')).toBe(false)
  })
})
