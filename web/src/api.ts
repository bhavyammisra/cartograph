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
export type Hit = FunctionRef & { rank: number }
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
