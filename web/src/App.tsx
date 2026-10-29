import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ask, DEMO, demoQuestions, type AgentEvent, type Health } from './api'
import { buildMap, OTHER_LINE, type CodeMap } from './buildGraph'
import FunctionPanel from './FunctionPanel'
import { buildJourney } from './journey'
import JourneyPanel from './JourneyPanel'
import LinesKey from './LinesKey'
import MapView from './MapView'
import SearchBox from './SearchBox'

type Load = { status: 'loading' } | { status: 'error' } | { status: 'ready'; health: Health; map: CodeMap }
type Run = {
  question: string
  events: AgentEvent[]
  status: 'running' | 'done' | 'error'
  started: number
  seconds: number | null
}

const REPLAY_MS = 900 // pause between steps when replaying
const recordedSeconds = (events: AgentEvent[]) =>
  events.reduce((t, e) => t + ('ms' in e && e.ms ? e.ms : 0), 0) / 1000
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export default function App() {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [selected, setSelected] = useState<string | null>(null)
  const [focusLine, setFocusLine] = useState<number | null>(null)
  const [flyTo, setFlyTo] = useState<{ node: string; nonce: number } | null>(null)
  const [run, setRun] = useState<Run | null>(null)
  const [shown, setShown] = useState(Infinity) // how many steps are visible (replay)
  const stopStream = useRef<(() => void) | null>(null)
  const [demoQs, setDemoQs] = useState<string[]>([])
  useEffect(() => { if (DEMO) demoQuestions().then(setDemoQs).catch(() => setDemoQs([])) }, [])

  const startAsk = useCallback((question: string) => {
    stopStream.current?.()
    setSelected(null)
    setShown(Infinity)
    const started = performance.now()
    setRun({ question, events: [], status: 'running', started, seconds: null })
    stopStream.current = ask(question, (e) => setRun((r) => {
      if (!r) return r
      const end = e.type === 'done' || e.type === 'error'
      return { ...r, events: [...r.events, e], status: e.type === 'done' ? 'done' : e.type === 'error' ? 'error' : r.status,
               // A demo replay is sped up: report the time the recorded run really took.
               seconds: !end ? r.seconds : DEMO ? recordedSeconds([...r.events, e])
                 : (performance.now() - r.started) / 1000 }
    }))
  }, [])

  useEffect(() => {
    // The map's labels are drawn on a canvas, which can't wait for a web font by itself.
    Promise.all([api.health(), api.graph(), document.fonts.load('12px "Archivo Variable"')])
      .then(([health, graph]) => {
        const map = buildMap(graph)
        setLoad({ status: 'ready', health, map })
        // Links open straight on a function (#f=123) or run a question (#ask=...).
        const linked = /^#f=(\d+)$/.exec(window.location.hash)?.[1]
        const question = /^#ask=(.+)$/.exec(window.location.hash)?.[1]
        if (linked && map.graph.hasNode(linked)) {
          setSelected(linked)
          setFlyTo({ node: linked, nonce: Date.now() })
        } else if (question) {
          startAsk(decodeURIComponent(question))
        }
      })
      .catch(() => setLoad({ status: 'error' }))
    return () => stopStream.current?.()
  }, [startAsk])

  const question = run?.question
  useEffect(() => {
    if (load.status !== 'ready') return
    const hash = selected ? `#f=${selected}` : question ? `#ask=${encodeURIComponent(question)}` : ''
    history.replaceState(null, '', hash || window.location.pathname)
  }, [selected, question, load.status])

  const closeRun = useCallback(() => {
    stopStream.current?.()
    setRun(null)
  }, [])

  // Escape steps back: from a function to its route, then from the route to the plain map.
  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (selected) setSelected(null)
      else if (run) closeRun()
    }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [selected, run, closeRun])

  const map = load.status === 'ready' ? load.map : null
  const colorOf = useCallback(
    (id: number) => (map?.graph.hasNode(String(id)) ? map.graph.getNodeAttribute(String(id), 'line') : OTHER_LINE),
    [map],
  )
  const nameOf = useCallback((handle: unknown) => {
    const id = /^F?(\d+)$/.exec(String(handle))?.[1]
    return id && map?.graph.hasNode(id) ? map.graph.getNodeAttribute(id, 'label') : String(handle)
  }, [map])
  const go = useCallback((id: number) => {
    const node = String(id)
    setSelected(node)
    setFlyTo({ node, nonce: Date.now() })
  }, [])

  const replay = useCallback(() => {
    if (!run || reducedMotion()) return setShown(Infinity)
    setSelected(null)
    setShown(0)
  }, [run])
  useEffect(() => {
    if (!run || shown >= run.events.length) return
    const t = setTimeout(() => setShown((n) => n + 1), REPLAY_MS)
    return () => clearTimeout(t)
  }, [shown, run])

  const visible = useMemo(() => run?.events.slice(0, shown) ?? [], [run, shown])
  const journey = useMemo(() => {
    if (!map || !run) return null
    // Real calls only: the map also holds temporary edges for the journey's search jumps.
    const real = (a: string, b: string) => map.graph.edges(a, b).some((e) => !e.startsWith('leg:'))
    return buildJourney(visible, (a, b) => real(a, b) || real(b, a))
  }, [map, run, visible])

  // The camera follows the agent: to each new stop, then to the destination.
  const lastStop = selected ? null : journey?.destinations.at(-1) ?? journey?.stops.at(-1)?.node ?? null

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
  const done = run?.events.find((e) => e.type === 'done')
  return (
    <div className={DEMO ? 'app demo' : 'app'}>
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
        <SearchBox onPick={go} onAsk={startAsk} asking={run?.status === 'running'} colorOf={colorOf} />
      </header>
      {DEMO && (
        <nav className="demo-bar" aria-label="About this demo">
          <span>Demo: name search and recorded agent runs. Try</span>
          {demoQs.map((q) => (
            <button type="button" className="text-button" key={q} onClick={() => startAsk(q)}>{q}</button>
          ))}
          <span className="demo-links">
            <a href="https://github.com/bhavyammisra/cartograph">Source</a>
            <a href="/privacy.html">Privacy</a>
            <a href="/terms.html">Terms</a>
          </span>
        </nav>
      )}
      <main className={selected || run ? 'stage with-panel' : 'stage'}>
        <MapView map={load.map} selected={selected} focusLine={focusLine} journey={selected ? null : journey}
                 onSelect={setSelected} flyTo={flyTo} follow={lastStop} />
        <LinesKey lines={load.map.lines} focus={focusLine} onFocus={setFocusLine} />
        {selected ? (
          <FunctionPanel id={Number(selected)} colorOf={colorOf} onPick={go} onClose={() => setSelected(null)}
                         onBack={run ? () => setSelected(null) : undefined} />
        ) : run && journey && (
          <JourneyPanel
            question={run.question} events={visible} journey={journey} status={run.status}
            seconds={run.seconds} tokens={done?.type === 'done' ? done.tokens : null}
            replaying={shown < run.events.length} nameOf={nameOf}
            placeOf={(id) => ({ path: load.map.graph.getNodeAttribute(id, 'path'),
                                line: load.map.graph.getNodeAttribute(id, 'line_no'), color: colorOf(Number(id)) })}
            onPick={go} onReplay={replay} onClose={closeRun}
          />
        )}
      </main>
    </div>
  )
}
