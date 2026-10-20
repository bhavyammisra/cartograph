import { Search } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { api, displayName, type Hit } from './api'

type Props = { onPick: (id: number) => void; colorOf: (id: number) => string }

/** Combobox: type a question or a name, arrow through results, Enter flies the map there. */
export default function SearchBox({ onPick, colorOf }: Props) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<Hit[] | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [active, setActive] = useState(0)
  const [open, setOpen] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const listId = useId()

  useEffect(() => {
    if (!q.trim()) return // cleared in onChange
    const ctrl = new AbortController()
    const t = setTimeout(() => {
      setStatus('loading')
      api.search(q.trim(), ctrl.signal)
        .then((h) => { setHits(h); setActive(0); setStatus('idle'); setOpen(true) })
        .catch((e) => { if (e.name !== 'AbortError') setStatus('error') })
    }, 250)
    return () => { clearTimeout(t); ctrl.abort() }
  }, [q])

  // "/" jumps to search from anywhere, the usual shortcut in developer tools.
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])

  const pick = (h: Hit) => { onPick(h.id); setOpen(false) }
  const showList = open && hits !== null

  return (
    <div className="search">
      <Search className="search-icon" size={16} aria-hidden />
      <input
        ref={input}
        type="search"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && hits!.length ? `${listId}-${active}` : undefined}
        aria-label="Search functions by name or by what they do"
        placeholder="Search: a name, or what the code does"
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          if (!e.target.value.trim()) { setHits(null); setStatus('idle') }
        }}
        onFocus={() => hits && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (!hits?.length) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => (a + 1) % hits.length) }
          if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => (a - 1 + hits.length) % hits.length) }
          if (e.key === 'Enter') { e.preventDefault(); pick(hits[active]) }
          if (e.key === 'Escape') setOpen(false)
        }}
      />
      <kbd className="search-key" aria-hidden>/</kbd>
      {status === 'loading' && <span className="search-status" role="status">Searching</span>}
      {status === 'error' && <span className="search-status error" role="status">Search failed</span>}
      {showList && (
        <ul id={listId} role="listbox" className="results" aria-label="Search results">
          {hits!.length === 0 && <li className="results-empty">No functions match</li>}
          {hits!.map((h, i) => (
            <li
              key={h.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'result active' : 'result'}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(h)}
              onMouseEnter={() => setActive(i)}
            >
              <span className="bullet" style={{ background: colorOf(h.id) }} aria-hidden />
              <span className="result-name">{displayName(h)}</span>
              <span className="result-path">{h.path}:{h.start_line}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
