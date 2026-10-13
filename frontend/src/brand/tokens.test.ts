import { describe, expect, it } from 'vitest'
import css from '../index.css?raw'

// Controllo di contrasto WCAG AA (4.5:1) sulle coppie testo/sfondo dei token.
const block = (selector: string) => {
  const m = css.match(new RegExp(`${selector.replace('.', '\\.')}\\s*\\{([^}]*)\\}`))
  if (!m) throw new Error('blocco ' + selector + ' non trovato')
  return Object.fromEntries([...m[1].matchAll(/--tecnia-([a-z-]+):\s*(\d+) (\d+) (\d+);/g)].map((x) => [x[1], [Number(x[2]), Number(x[3]), Number(x[4])]]))
}
const lum = ([r, g, b]: number[]) => {
  const f = (v: number) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
const ratio = (a: number[], b: number[]) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05) }

describe.each([[':root', 'chiaro'], ['.dark', 'scuro']])('token %s (%s)', (selector) => {
  const t = block(selector)
  const white = [255, 255, 255]
  it.each(['ink', 'muted', 'primary', 'magenta-deep', 'ok'])('%s ha contrasto AA sullo sfondo', (name) => {
    expect(ratio(t[name], t.bg)).toBeGreaterThanOrEqual(4.5)
  })
  it('il testo principale ha contrasto AA anche sulle superfici', () => {
    const surface = selector === ':root' ? white : [15, 23, 42]
    expect(ratio(t.ink, surface)).toBeGreaterThanOrEqual(4.5)
    expect(ratio(t.muted, surface)).toBeGreaterThanOrEqual(4.5)
  })
})
