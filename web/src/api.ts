// Shapes returned by the Python API (engine/src/cartograph/api.py).

export type FunctionRef = {
  id: number
  name: string
  qualname: string
  path: string
  start_line: number
  end_line: number
  kind: string // tree-sitter node type, or "module" for a file's top-level code
}

export type Edge = { source: number; target: number; via: string }
export type GraphData = { nodes: FunctionRef[]; edges: Edge[] }
/** rank: merged position; keyword_rank / meaning_rank: where each method alone put it (null: not
 * in its top 50). These are the "why this result" for search. */
export type Hit = FunctionRef & { rank: number; keyword_rank: number | null; meaning_rank: number | null }

/** One message from the agent's live stream (/api/ask), mirroring agent.py's events. */
export type AgentEvent =
  | { type: 'tool'; step: number; tool: string; args: Record<string, unknown>; ids: number[]; ms: number }
  | { type: 'answer'; step: number; ids: number[]; args?: Record<string, unknown>; from_text?: boolean; ms?: number }
  | { type: 'text'; step: number; text: string }
  | { type: 'error'; step?: number; text: string }
  | { type: 'done'; answer: number[]; not_found: boolean; ranked: number[]; tokens: number }

/** Opens the agent stream; returns a function that stops it. */
export function ask(q: string, onEvent: (e: AgentEvent) => void): () => void {
  if (DEMO) return replayDemo(q, onEvent)
  const source = new EventSource(`/api/ask?q=${encodeURIComponent(q)}`)
  source.onmessage = (m) => {
    const e = JSON.parse(m.data) as AgentEvent
    onEvent(e)
    if (e.type === 'done' || e.type === 'error') source.close()
  }
  source.onerror = () => {
    if (source.readyState !== EventSource.CLOSED) onEvent({ type: 'error', text: 'Lost the connection to the API.' })
    source.close()
  }
  return () => source.close()
}
export type FunctionDetail = FunctionRef & {
  code: string
  callers: FunctionRef[]
  callees: FunctionRef[]
  /** From git history: functions edited in the same commits, and in how many. */
  changed_with: (FunctionRef & { times: number })[]
}
export type Health = { ok: boolean; root: string; functions: number }

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal })
  if (!res.ok) throw new Error(`${path} answered ${res.status}`)
  return res.json() as Promise<T>
}

/** The demo site (`VITE_DEMO=1 npm run build`) reads files from `cartograph export` instead of
 * the engine: name search only, and the agent replays recorded questions. */
export const DEMO = import.meta.env.VITE_DEMO === '1'
let demoGraph: Promise<GraphData> | null = null
let demoTraces: Promise<Record<string, AgentEvent[]>> | null = null
export const demoQuestions = () => (demoTraces ??= get('/demo/traces.json')).then(Object.keys)

function demoSearch(q: string): Promise<Hit[]> {
  const words = q.toLowerCase().split(/\s+/).filter(Boolean)
  return (demoGraph ??= get<GraphData>('/demo/graph.json')).then((g) => g.nodes
    .filter((n) => n.kind !== 'module' && words.every((w) => `${n.qualname} ${n.path}`.toLowerCase().includes(w)))
    .slice(0, 10)
    .map((n, i) => ({ ...n, rank: i + 1, keyword_rank: null, meaning_rank: null })))
}

export const api = DEMO ? {
  health: () => get<Health>('/demo/health.json'),
  graph: () => (demoGraph ??= get<GraphData>('/demo/graph.json')),
  fn: (id: number, signal?: AbortSignal) => get<FunctionDetail>(`/demo/functions/${id}.json`, signal),
  search: (q: string) => demoSearch(q),
} : {
  health: () => get<Health>('/api/health'),
  graph: () => get<GraphData>('/api/graph'),
  fn: (id: number, signal?: AbortSignal) => get<FunctionDetail>(`/api/functions/${id}`, signal),
  search: (q: string, signal?: AbortSignal) =>
    get<Hit[]>(`/api/search?mode=hybrid&k=10&q=${encodeURIComponent(q)}`, signal),
}

/** Plays a recorded run at its own pace (each step capped at 1.5 s). */
function replayDemo(q: string, onEvent: (e: AgentEvent) => void): () => void {
  let stopped = false
  const timers: number[] = []
  ;(demoTraces ??= get('/demo/traces.json')).then((traces) => {
    const events = traces[q]
    if (!events) {
      onEvent({ type: 'error', text: 'This demo replays recorded questions only. Pick one from the list.' })
      return
    }
    let at = 0
    for (const e of events) {
      at += Math.min('ms' in e && e.ms ? e.ms : 400, 1500)
      timers.push(window.setTimeout(() => !stopped && onEvent(e), at))
    }
  })
  return () => { stopped = true; timers.forEach(clearTimeout) }
}

/** How a function is shown to people: anonymous functions get their line instead. */
export function displayName(f: Pick<FunctionRef, 'qualname' | 'start_line' | 'kind' | 'path'>) {
  if (f.kind === 'module') return `${f.path} (top level)`
  return f.qualname === '<anonymous>' ? `anonymous, line ${f.start_line}` : f.qualname
}
