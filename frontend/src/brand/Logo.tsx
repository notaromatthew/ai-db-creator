// Marchio AI-DB-Creator (proposta B): tre tabelle e un riquadro in gradiente con la scintilla.
export function LogoMark({ size = 32, className = '' }: { size?: number; className?: string }) {
  const id = 'aidb-g-' + size
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width={size} height={size} role="img" aria-label="AI-DB-Creator" className={className}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff6b00" />
          <stop offset="1" stopColor="#fe3ac6" />
        </linearGradient>
      </defs>
      <g fill="none" stroke="currentColor" strokeWidth="3.2">
        <rect x="6" y="6" width="25" height="25" rx="7" />
        <rect x="6" y="33" width="25" height="25" rx="7" />
        <rect x="33" y="33" width="25" height="25" rx="7" />
      </g>
      <rect x="33" y="6" width="25" height="25" rx="7" fill={`url(#${id})`} />
      <path d="M45.5 11l1.5 4.5 4.5 1.5-4.5 1.5-1.5 4.5-1.5-4.5-4.5-1.5 4.5-1.5z" fill="#fff" />
    </svg>
  )
}

export function Logo({ size = 32, showName = true }: { size?: number; showName?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5 text-tecnia-ink dark:text-white">
      <LogoMark size={size} />
      {showName && <span className="font-headline text-lg font-bold tracking-tight">AI-DB-Creator</span>}
    </span>
  )
}
