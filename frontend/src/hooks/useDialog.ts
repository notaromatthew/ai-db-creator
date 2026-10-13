import { useEffect, useRef } from 'react'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Comportamento accessibile per le modali: focus iniziale dentro il dialogo,
 * focus bloccato con Tab, chiusura con Esc e ripristino del focus alla chiusura.
 */
export function useDialog<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const ref = useRef<T>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    const node = ref.current
    const items = () => (node ? Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)) : [])
    const first = node?.querySelector<HTMLElement>('[data-autofocus]') ?? items()[0]
    first?.focus()

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        closeRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const list = items()
      if (!list.length) return
      const head = list[0]
      const tail = list[list.length - 1]
      const active = document.activeElement
      if (event.shiftKey && (active === head || !node?.contains(active))) {
        event.preventDefault(); tail.focus()
      } else if (!event.shiftKey && (active === tail || !node?.contains(active))) {
        event.preventDefault(); head.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
  }, [open])

  return ref
}
