import { X } from 'lucide-react'
import { Highlight } from 'prism-react-renderer'
import { useEffect, useState } from 'react'
import { api, displayName, type FunctionDetail, type FunctionRef } from './api'

type Props = {
  id: number
  colorOf: (id: number) => string
  onPick: (id: number) => void
  onClose: () => void
}

// Token colours come from CSS (.token.keyword etc.), so the code follows the theme.
const CLASS_ONLY_THEME = { plain: {}, styles: [] }

function Connections({ title, items, colorOf, onPick }: {
  title: string; items: FunctionRef[]; colorOf: (id: number) => string; onPick: (id: number) => void
}) {
  return (
    <section className="connections" aria-label={title}>
      <h3>{title} <span className="count">{items.length}</span></h3>
      {items.length === 0 ? <p className="none">None found</p> : (
        <ul>
          {items.map((f) => (
            <li key={f.id}>
              <button type="button" onClick={() => onPick(f.id)}>
                <span className="bullet" style={{ background: colorOf(f.id) }} aria-hidden />
                <span className="conn-name">{displayName(f)}</span>
                <span className="conn-path">{f.path}:{f.start_line}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** The station sign: line bullet, function name, file and lines, then code and connections. */
export default function FunctionPanel({ id, colorOf, onPick, onClose }: Props) {
  const [loaded, setFn] = useState<FunctionDetail | null>(null)
  const [failedId, setFailedId] = useState<number | null>(null)
  const error = failedId === id
  const fn = loaded?.id === id ? loaded : null // never show the previous function's details

  useEffect(() => {
    const ctrl = new AbortController()
    api.fn(id, ctrl.signal).then(setFn).catch((e) => e.name !== 'AbortError' && setFailedId(id))
    return () => ctrl.abort()
  }, [id])

  return (
    <aside className="panel" aria-label="Function details">
      <header className="sign">
        <span className="sign-bullet" style={{ background: colorOf(id) }} aria-hidden />
        <div className="sign-text">
          <h2>{fn ? displayName(fn) : error ? 'Could not load' : 'Loading'}</h2>
          {fn && <p className="sign-where">{fn.path} <span>lines {fn.start_line} to {fn.end_line}</span></p>}
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close details">
          <X size={18} aria-hidden />
        </button>
      </header>
      {error && <p className="panel-error">The API did not return this function. Is <code>cartograph serve</code> still running?</p>}
      {fn && (
        <div className="panel-body">
          <Highlight code={fn.code.replace(/\s+$/, '')} language="javascript" theme={CLASS_ONLY_THEME}>
            {({ tokens, getLineProps, getTokenProps }) => (
              <pre className="code" tabIndex={0} aria-label={`Code of ${displayName(fn)}`}>
                {tokens.map((line, i) => {
                  const { key: _k, ...lineProps } = getLineProps({ line, key: i })
                  return (
                    <div key={i} {...lineProps} className="code-line">
                      <span className="code-no" aria-hidden>{fn.start_line + i}</span>
                      <span>
                        {line.map((token, j) => {
                          const { key: _t, ...props } = getTokenProps({ token, key: j })
                          return <span key={j} {...props} />
                        })}
                      </span>
                    </div>
                  )
                })}
              </pre>
            )}
          </Highlight>
          <Connections title="Called by" items={fn.callers} colorOf={colorOf} onPick={onPick} />
          <Connections title="Calls" items={fn.callees} colorOf={colorOf} onPick={onPick} />
        </div>
      )}
    </aside>
  )
}
