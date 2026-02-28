/**
 * Lightweight markdown-to-React renderer.
 * Handles: **bold**, ### headings, | tables |, bullet lists, line breaks.
 * No external dependencies.
 */

function inlineFormat(text) {
  if (!text) return text
  const parts = []
  let remaining = text
  let key = 0
  while (remaining) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    if (!boldMatch) {
      parts.push(remaining)
      break
    }
    const idx = boldMatch.index
    if (idx > 0) parts.push(remaining.slice(0, idx))
    parts.push(<strong key={key++}>{boldMatch[1]}</strong>)
    remaining = remaining.slice(idx + boldMatch[0].length)
  }
  return parts
}

function parseTable(lines) {
  const rows = lines
    .filter(l => !l.match(/^\|[\s-:|]+\|$/))
    .map(l =>
      l.split('|').slice(1, -1).map(cell => cell.trim())
    )
  if (rows.length === 0) return null
  const [header, ...body] = rows

  return (
    <div className="formatted-table-wrap">
      <table className="formatted-table">
        {header && (
          <thead>
            <tr>{header.map((h, i) => <th key={i}>{inlineFormat(h)}</th>)}</tr>
          </thead>
        )}
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{inlineFormat(cell)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FormattedText({ text }) {
  if (!text) return null

  const lines = text.split('\n')
  const elements = []
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Skip empty lines
    if (!line.trim()) {
      i++
      continue
    }

    // Headings (### or ##)
    const headingMatch = line.match(/^(#{1,4})\s+(.+)/)
    if (headingMatch) {
      const level = headingMatch[1].length
      const content = headingMatch[2].replace(/\*\*/g, '')
      elements.push(
        <div key={key++} className={`formatted-h${level}`}>
          {content}
        </div>
      )
      i++
      continue
    }

    // Table block (consecutive lines starting with |)
    if (line.trim().startsWith('|')) {
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim())
        i++
      }
      elements.push(<div key={key++}>{parseTable(tableLines)}</div>)
      continue
    }

    // Bullet list items (- or *)
    if (line.match(/^\s*[-*]\s+/)) {
      const listItems = []
      while (i < lines.length && lines[i].match(/^\s*[-*]\s+/)) {
        listItems.push(lines[i].replace(/^\s*[-*]\s+/, ''))
        i++
      }
      elements.push(
        <ul key={key++} className="formatted-list">
          {listItems.map((item, li) => <li key={li}>{inlineFormat(item)}</li>)}
        </ul>
      )
      continue
    }

    // Numbered list items (1. 2. etc)
    if (line.match(/^\s*\d+\.\s+/)) {
      const listItems = []
      while (i < lines.length && lines[i].match(/^\s*\d+\.\s+/)) {
        listItems.push(lines[i].replace(/^\s*\d+\.\s+/, ''))
        i++
      }
      elements.push(
        <ol key={key++} className="formatted-list">
          {listItems.map((item, li) => <li key={li}>{inlineFormat(item)}</li>)}
        </ol>
      )
      continue
    }

    // Regular paragraph
    elements.push(
      <p key={key++} className="formatted-p">{inlineFormat(line)}</p>
    )
    i++
  }

  return <div className="formatted-text">{elements}</div>
}
