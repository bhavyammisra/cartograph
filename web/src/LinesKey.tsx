import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { Line } from './buildGraph'

type Props = { lines: Line[]; focus: number | null; onFocus: (id: number | null) => void }

const SHOWN = 8 // lines with their own colour; the rest share one

/** The map key: what the colours mean, and a way to light up one neighbourhood. */
export default function LinesKey({ lines, focus, onFocus }: Props) {
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 760px)').matches)
  const others = lines.slice(SHOWN)
  return (
    <section className="key" aria-label="Map key">
      <button type="button" className="key-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        Lines <ChevronDown size={14} aria-hidden className={open ? 'chev open' : 'chev'} />
      </button>
      {open && (
        <>
          <ul>
            {lines.slice(0, SHOWN).map((l) => (
              <li key={l.id}>
                <button
                  type="button"
                  aria-pressed={focus === l.id}
                  className={focus === l.id ? 'key-line on' : 'key-line'}
                  onClick={() => onFocus(focus === l.id ? null : l.id)}
                >
                  <span className="key-swatch" style={{ background: l.color }} aria-hidden />
                  <span className="key-label">{l.label}</span>
                  <span className="count" aria-label={`${l.size} stations`}>{l.size}</span>
                  <span className="key-path">{l.hubPath}</span>
                </button>
              </li>
            ))}
          </ul>
          {others.length > 0 && (
            <p className="key-note">
              <span className="key-swatch other" aria-hidden /> {others.length} smaller lines,{' '}
              {others.reduce((s, l) => s + l.size, 0)} stations
            </p>
          )}
          <p className="key-note">
            Lines are named after their busiest station. Ring: a function. Solid: a file's
            top-level code. Bigger stops have more calls.
          </p>
        </>
      )}
    </section>
  )
}
