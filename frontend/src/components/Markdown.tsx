import { Fragment, ReactNode } from 'react'

const INLINE = /(\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\*[^*\s][^*\n]*\*|_[^_\s][^_\n]*_)/g

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(INLINE).filter((part) => part !== '').map((part, i) => {
    const key = `${keyPrefix}-${i}`
    if (/^\*\*[^*]+\*\*$/.test(part) || /^__[^_]+__$/.test(part)) return <strong key={key}>{part.slice(2, -2)}</strong>
    if (/^`[^`]+`$/.test(part)) return <code key={key} className="rounded bg-black/10 px-1 font-mono text-[0.85em] dark:bg-white/10">{part.slice(1, -1)}</code>
    if (/^\*[^*]+\*$/.test(part) || /^_[^_]+_$/.test(part)) return <em key={key}>{part.slice(1, -1)}</em>
    return <Fragment key={key}>{part}</Fragment>
  })
}

type Block = { kind: 'p'; lines: string[] } | { kind: 'ul' | 'ol'; items: string[] }

function parseBlocks(source: string): Block[] {
  const blocks: Block[] = []
  for (const raw of source.replace(/\r\n/g, '\n').split('\n')) {
    const line = raw.trim()
    const bullet = /^[-*•]\s+(.*)$/.exec(line)
    const numbered = /^\d+[.)]\s+(.*)$/.exec(line)
    const last = blocks[blocks.length - 1]
    if (!line) {
      blocks.push({ kind: 'p', lines: [] })
    } else if (bullet) {
      if (last?.kind === 'ul') last.items.push(bullet[1])
      else blocks.push({ kind: 'ul', items: [bullet[1]] })
    } else if (numbered) {
      if (last?.kind === 'ol') last.items.push(numbered[1])
      else blocks.push({ kind: 'ol', items: [numbered[1]] })
    } else {
      const heading = /^#{1,6}\s+/.test(line)
      const content = heading ? `**${line.replace(/^#{1,6}\s+/, '')}**` : line
      if (last?.kind === 'p') last.lines.push(content)
      else blocks.push({ kind: 'p', lines: [content] })
    }
  }
  return blocks.filter((b) => (b.kind === 'p' ? b.lines.length > 0 : true))
}

/** Markdown minimo e sicuro (grassetto, corsivo, codice, elenchi, titoli): niente HTML, niente link. */
export default function Markdown({ text }: { text: string }) {
  const blocks = parseBlocks(text)
  return (
    <div className="space-y-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5">
      {blocks.map((b, i) => {
        if (b.kind !== 'p') {
          const Tag = b.kind
          return <Tag key={i}>{b.items.map((item, j) => <li key={j}>{renderInline(item, `${i}-${j}`)}</li>)}</Tag>
        }
        return (
          <p key={i}>
            {b.lines.map((line, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {renderInline(line, `${i}-${j}`)}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}
