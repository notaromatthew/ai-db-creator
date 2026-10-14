import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Markdown from './Markdown'

describe('Markdown', () => {
  it('rende grassetto, corsivo e codice senza mostrare i simboli', () => {
    const { container } = render(<Markdown text={'Aggiungo **email** ai *clienti* e `note`.'} />)
    expect(container.querySelector('strong')?.textContent).toBe('email')
    expect(container.querySelector('em')?.textContent).toBe('clienti')
    expect(container.querySelector('code')?.textContent).toBe('note')
    expect(container.textContent).not.toContain('**')
  })

  it('rende elenchi puntati e numerati', () => {
    const { container } = render(<Markdown text={'Propongo:\n- una tabella **ordini**\n- una colonna data\n\n1. primo\n2. secondo'} />)
    expect(container.querySelectorAll('ul li')).toHaveLength(2)
    expect(container.querySelectorAll('ol li')).toHaveLength(2)
    expect(screen.getByText('ordini').tagName).toBe('STRONG')
  })

  it('trasforma i titoli in grassetto e non esegue HTML', () => {
    const { container } = render(<Markdown text={'## Proposta\n<img src=x onerror=alert(1)> [link](http://x)'} />)
    expect(container.querySelector('strong')?.textContent).toBe('Proposta')
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('a')).toBeNull()
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>')
  })
})
