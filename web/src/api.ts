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
}
export type Health = { ok: boolean; root: string; functions: number }

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal })
  if (!res.ok) throw new Error(`${path} answered ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<Health>('/api/health'),
  graph: () => get<GraphData>('/api/graph'),
  fn: (id: number, signal?: AbortSignal) => get<FunctionDetail>(`/api/functions/${id}`, signal),
  search: (q: string, signal?: AbortSignal) =>
    get<Hit[]>(`/api/search?mode=hybrid&k=10&q=${encodeURIComponent(q)}`, signal),
}

/** How a function is shown to people: anonymous functions get their line instead. */
export function displayName(f: Pick<FunctionRef, 'qualname' | 'start_line' | 'kind' | 'path'>) {
  if (f.kind === 'module') return `${f.path} (top level)`
  return f.qualname === '<anonymous>' ? `anonymous, line ${f.start_line}` : f.qualname
}
