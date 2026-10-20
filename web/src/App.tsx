import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type Health } from './api'
import { buildMap, OTHER_LINE, type CodeMap } from './buildGraph'
import FunctionPanel from './FunctionPanel'
import LinesKey from './LinesKey'
import MapView from './MapView'
import SearchBox from './SearchBox'

type Load = { status: 'loading' } | { status: 'error' } | { status: 'ready'; health: Health; map: CodeMap }

export default function App() {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [selected, setSelected] = useState<string | null>(null)
  const [focusLine, setFocusLine] = useState<number | null>(null)
  const [flyTo, setFlyTo] = useState<{ node: string; nonce: number } | null>(null)

  useEffect(() => {
    // The map's labels are drawn on a canvas, which can't wait for a web font by itself.
    Promise.all([api.health(), api.graph(), document.fonts.load('12px "Archivo Variable"')])
      .then(([health, graph]) => {
        const map = buildMap(graph)
        setLoad({ status: 'ready', health, map })
        // A link like #f=123 opens straight on that function.
        const linked = /^#f=(\d+)$/.exec(window.location.hash)?.[1]
        if (linked && map.graph.hasNode(linked)) {
          setSelected(linked)
          setFlyTo({ node: linked, nonce: Date.now() })
        }
      })
      .catch(() => setLoad({ status: 'error' }))
  }, [])

  useEffect(() => {
    if (load.status !== 'ready') return
    history.replaceState(null, '', selected ? `#f=${selected}` : window.location.pathname)
  }, [selected, load.status])

  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setSelected(null) }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [])

  const map = load.status === 'ready' ? load.map : null
  const colorOf = useCallback(
    (id: number) => (map?.graph.hasNode(String(id)) ? map.graph.getNodeAttribute(String(id), 'line') : OTHER_LINE),
    [map],
  )
  const go = useCallback((id: number) => {
    const node = String(id)
    setSelected(node)
    setFlyTo({ node, nonce: Date.now() })
  }, [])

  const stats = useMemo(() => {
    if (!map) return null
    let functions = 0, files = 0
    map.graph.forEachNode((_, a) => { if (a.kind === 'function') functions++; else if (a.kind === 'file') files++ })
    return { functions, files, calls: map.calls }
  }, [map])

  if (load.status !== 'ready') {
    return (
      <main className="state">
        <h1>Cartograph</h1>
        {load.status === 'loading'
          ? <p role="status">Drawing the map</p>
          : <p role="alert">Can't reach the Cartograph API. Start it from the repository root with{' '}
              <code>uv run --project engine cartograph serve path/to/repo</code>, then reload.</p>}
      </main>
    )
  }

  const repo = load.health.root.split('/').pop()
  return (
    <div className="app">
      <header className="bar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={22} height={22} />
          <span className="name">Cartograph</span>
          <span className="repo">{repo}</span>
        </div>
        {stats && (
          <p className="stats" aria-label="Map size">
            <span><b>{stats.functions}</b> functions</span>
            <span><b>{stats.files}</b> files</span>
            <span><b>{stats.calls}</b> calls</span>
          </p>
        )}
        <SearchBox onPick={go} colorOf={colorOf} />
      </header>
      <main className={selected ? 'stage with-panel' : 'stage'}>
        <MapView map={load.map} selected={selected} focusLine={focusLine} onSelect={setSelected} flyTo={flyTo} />
        <LinesKey lines={load.map.lines} focus={focusLine} onFocus={setFocusLine} />
        {selected && (
          <FunctionPanel id={Number(selected)} colorOf={colorOf} onPick={go} onClose={() => setSelected(null)} />
        )}
      </main>
    </div>
  )
}
