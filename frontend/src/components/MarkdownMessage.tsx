import React from 'react'

interface Props {
  content: string
  className?: string
}

function renderInline(text: string): React.ReactNode[] {
  // Regex to split inline elements: code, bold, italic, links
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|(?<!\*)\*[^*]+\*(?!\*)|(?<!_)_[^_]+_(?!_)|\[[^\]]+\]\([^)]+\))/g
  const parts = text.split(regex)

  return parts.map((part, idx) => {
    if (!part) return null

    // Inline code
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={idx}
          className="rounded bg-slate-200/80 px-1.5 py-0.5 font-mono text-[12px] font-semibold text-pink-600 dark:bg-slate-800 dark:text-pink-400"
        >
          {part.slice(1, -1)}
        </code>
      )
    }

    // Bold
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      return (
        <strong key={idx} className="font-bold text-slate-900 dark:text-white">
          {renderInline(part.slice(2, -2))}
        </strong>
      )
    }

    // Italic
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      return (
        <em key={idx} className="italic text-slate-800 dark:text-slate-200">
          {renderInline(part.slice(1, -1))}
        </em>
      )
    }

    // Link
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (linkMatch) {
      return (
        <a
          key={idx}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-blue-600 underline hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {linkMatch[1]}
        </a>
      )
    }

    return <React.Fragment key={idx}>{part}</React.Fragment>
  })
}

export default function MarkdownMessage({ content, className = '' }: Props) {
  if (!content) return null

  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let inCodeBlock = false
  let codeBlockLang = ''
  let codeLines: string[] = []
  let inTable = false
  let tableRows: string[][] = []
  let tableHeader: string[] = []

  const flushTable = (keyIdx: number) => {
    if (tableRows.length > 0 || tableHeader.length > 0) {
      elements.push(
        <div key={`table-${keyIdx}`} className="my-2.5 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs dark:divide-slate-800">
            {tableHeader.length > 0 && (
              <thead className="bg-slate-100 dark:bg-slate-800/80">
                <tr>
                  {tableHeader.map((th, hIdx) => (
                    <th key={hIdx} className="px-3 py-2 font-bold text-slate-900 dark:text-slate-100">
                      {renderInline(th.trim())}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-800/60 dark:bg-slate-900/50">
              {tableRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3 py-1.5 text-slate-750 dark:text-slate-250">
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      tableHeader = []
      tableRows = []
      inTable = false
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i]
    const trimmed = rawLine.trim()

    // Fenced Code Block
    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        // Close code block
        elements.push(
          <div key={`code-${i}`} className="my-2.5 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 shadow-sm">
            {codeBlockLang && (
              <div className="border-b border-slate-800 bg-slate-950/80 px-3 py-1 text-[11px] font-mono text-slate-400">
                {codeBlockLang}
              </div>
            )}
            <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed text-emerald-400">
              <code>{codeLines.join('\n')}</code>
            </pre>
          </div>
        )
        codeLines = []
        codeBlockLang = ''
        inCodeBlock = false
      } else {
        // Flush table if open
        if (inTable) flushTable(i)
        inCodeBlock = true
        codeBlockLang = trimmed.slice(3).trim()
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(rawLine)
      continue
    }

    // Markdown Table
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2) {
      const cells = trimmed
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim())

      const isSeparator = cells.every((c) => /^:?-+:?$/.test(c))
      if (isSeparator) {
        // Divider line between header and body
        continue
      }

      if (!inTable) {
        inTable = true
        tableHeader = cells
      } else {
        tableRows.push(cells)
      }
      continue
    } else if (inTable) {
      flushTable(i)
    }

    // Headers
    if (trimmed.startsWith('#### ')) {
      elements.push(
        <h4 key={i} className="mb-1 mt-2.5 text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
          {renderInline(trimmed.slice(5))}
        </h4>
      )
      continue
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="mb-1 mt-3 text-sm font-bold text-slate-900 dark:text-white">
          {renderInline(trimmed.slice(4))}
        </h3>
      )
      continue
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="mb-1.5 mt-3.5 text-base font-bold text-slate-900 dark:text-white">
          {renderInline(trimmed.slice(3))}
        </h2>
      )
      continue
    }
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="mb-2 mt-4 text-lg font-extrabold text-slate-900 dark:text-white">
          {renderInline(trimmed.slice(2))}
        </h1>
      )
      continue
    }

    // Horizontal Rule
    if (/^(\*\*\*|---|___)$/.test(trimmed)) {
      elements.push(<hr key={i} className="my-3 border-slate-200 dark:border-slate-800" />)
      continue
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote
          key={i}
          className="my-1.5 rounded-r border-l-4 border-blue-500 bg-blue-50/50 py-1 pl-3 text-xs italic text-slate-700 dark:bg-blue-950/20 dark:text-slate-300"
        >
          {renderInline(trimmed.slice(2))}
        </blockquote>
      )
      continue
    }

    // Unordered List
    if (/^[-*]\s+/.test(trimmed)) {
      const itemText = trimmed.replace(/^[-*]\s+/, '')
      elements.push(
        <div key={i} className="my-0.5 flex items-start gap-2 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
          <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
          <span>{renderInline(itemText)}</span>
        </div>
      )
      continue
    }

    // Ordered List
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/)
    if (numMatch) {
      elements.push(
        <div key={i} className="my-0.5 flex items-start gap-2 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
          <span className="flex-shrink-0 font-semibold text-blue-600 dark:text-blue-400">
            {numMatch[1]}.
          </span>
          <span>{renderInline(numMatch[2])}</span>
        </div>
      )
      continue
    }

    // Empty line
    if (!trimmed) {
      elements.push(<div key={i} className="h-1.5" />)
      continue
    }

    // Standard Paragraph
    elements.push(
      <p key={i} className="my-0.5 text-xs leading-relaxed text-slate-800 dark:text-slate-200">
        {renderInline(rawLine)}
      </p>
    )
  }

  // Flush any remaining code block or table
  if (inCodeBlock && codeLines.length > 0) {
    elements.push(
      <div key="code-end" className="my-2.5 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 shadow-sm">
        <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed text-emerald-400">
          <code>{codeLines.join('\n')}</code>
        </pre>
      </div>
    )
  }
  if (inTable) {
    flushTable(lines.length)
  }

  return <div className={`space-y-0.5 ${className}`}>{elements}</div>
}
