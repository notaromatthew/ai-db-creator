import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Stepper from './Stepper'
import ActionBar from './ActionBar'
import DialectPicker from './DialectPicker'
import GenerationProgress from './GenerationProgress'

describe('Stepper', () => {
  it('marks the current step, completed steps and blocks unreachable ones', () => {
    const onSelect = vi.fn()
    render(<Stepper current={2} reachable={3} onSelect={onSelect} />)
    expect(screen.getByRole('button', { name: /schema/i })).toHaveAttribute('aria-current', 'step')
    expect(screen.getByRole('button', { name: /documenti/i })).toHaveTextContent('completato')
    expect(screen.getByRole('button', { name: /dati/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /documenti/i }))
    expect(onSelect).toHaveBeenCalledWith(1)
    fireEvent.click(screen.getByRole('button', { name: /database/i }))
    expect(onSelect).toHaveBeenCalledWith(3)
  })
})

describe('ActionBar', () => {
  it('shows step number, note and wires back and primary actions', () => {
    const back = vi.fn()
    const primary = vi.fn()
    render(<ActionBar step={3} info="Schema in bozza" note="Hai accesso in sola lettura." back={{ label: 'Indietro', onClick: back }} primary={{ label: 'Rendi definitivo', onClick: primary }} />)
    expect(screen.getByText(/passo 3 di 4/i)).toBeInTheDocument()
    expect(screen.getByText(/sola lettura/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /indietro/i }))
    fireEvent.click(screen.getByRole('button', { name: /rendi definitivo/i }))
    expect(back).toHaveBeenCalled()
    expect(primary).toHaveBeenCalled()
  })

  it('disables the primary action while loading or disabled', () => {
    const primary = vi.fn()
    const { rerender } = render(<ActionBar step={4} primary={{ label: 'Genera i dati', onClick: primary, disabled: true }} />)
    expect(screen.getByRole('button', { name: /genera i dati/i })).toBeDisabled()
    rerender(<ActionBar step={4} primary={{ label: 'Genera i dati', onClick: primary, loading: true }} />)
    expect(screen.getByRole('button', { name: /genera i dati/i })).toBeDisabled()
  })
})

describe('DialectPicker', () => {
  it('offers the four dialects and reports the choice', () => {
    const onChange = vi.fn()
    render(<DialectPicker value="postgresql" onChange={onChange} />)
    const radios = screen.getAllByRole('radio')
    expect(radios).toHaveLength(4)
    expect(screen.getByRole('radio', { name: /postgresql/i })).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(screen.getByRole('radio', { name: /sql server/i }))
    expect(onChange).toHaveBeenCalledWith('mssql')
    fireEvent.click(screen.getByRole('radio', { name: /sqlite/i }))
    expect(onChange).toHaveBeenCalledWith('sqlite')
    fireEvent.click(screen.getByRole('radio', { name: /mysql/i }))
    expect(onChange).toHaveBeenCalledWith('mysql')
  })
})

describe('GenerationProgress', () => {
  it('shows progress and the way back to the project list', () => {
    render(<MemoryRouter><GenerationProgress progress={50} /></MemoryRouter>)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
    expect(screen.getByRole('link', { name: /torna ai progetti/i })).toHaveAttribute('href', '/app')
  })
})
