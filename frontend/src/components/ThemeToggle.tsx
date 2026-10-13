import { useTheme } from '@/hooks/useTheme'

export default function ThemeToggle() {
  const { dark, toggle } = useTheme()
  return (
    <button
      type="button"
      onClick={toggle}
      className="grid h-10 w-10 place-items-center rounded-xl border border-tecnia-line bg-white/70 text-tecnia-ink transition-colors hover:bg-orange-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      aria-label={dark ? 'Attiva il tema chiaro' : 'Attiva il tema scuro'}
      aria-pressed={dark}
      title={dark ? 'Tema chiaro' : 'Tema scuro'}
    >
      <span className="material-symbols-outlined" aria-hidden="true">{dark ? 'light_mode' : 'dark_mode'}</span>
    </button>
  )
}
