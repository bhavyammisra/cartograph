// Turns the API's call graph into a laid-out, coloured map: stations (functions), lines
// (neighbourhoods found by Louvain) and district labels (one per file).

import Graph from 'graphology'
import louvain from 'graphology-communities-louvain'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import { displayName, type GraphData } from './api'

export type Line = { id: number; color: string; label: string; hubPath: string; size: number }
export type CodeMap = { graph: Graph; lines: Line[]; lineOf: Map<string, number>; calls: number }

const LANDMARKS = 12 // files labelled when zoomed out: the biggest, so labels don't pile up

/** Map label for a file: its folder and name, e.g. "view-locals/index.js". */
const shortPath = (path: string) => path.split('/').slice(-2).join('/')

// Enamel line colours, in order of line size. Beyond these, lines share a neutral colour.
// No yellow or amber: yellow is reserved for the route (see --route-* in index.css).
export const LINE_COLORS = [
  '#d6362c', '#00843d', '#0b4fa8', '#c2337a', '#ef6a1a', '#8c4799', '#8a5a2b', '#0098b3',
]
export const OTHER_LINE = '#8d9196'

/** Small seeded random generator, so the same codebase always draws the same map. */
function rng(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function buildMap(data: GraphData): CodeMap {
  const random = rng(42)
  const files = [...new Set(data.nodes.map((n) => n.path))].sort()

  // Layout graph: calls plus a light "same file" pull, so a file's functions stay together
  // even when they don't call each other.
  const layout = new Graph({ type: 'undirected' })
  files.forEach((path, i) => {
    const angle = (2 * Math.PI * i) / files.length
    layout.addNode(`file:${path}`, { x: Math.cos(angle) * 100, y: Math.sin(angle) * 100 })
  })
  for (const n of data.nodes) {
    const anchor = layout.getNodeAttributes(`file:${n.path}`)
    layout.addNode(String(n.id), { x: anchor.x + random() * 10, y: anchor.y + random() * 10 })
    layout.addEdge(String(n.id), `file:${n.path}`, { weight: 1 })
  }
  for (const e of data.edges) {
    const [a, b] = [String(e.source), String(e.target)]
    if (a === b) continue
    if (layout.hasEdge(a, b)) layout.updateEdgeAttribute(a, b, 'weight', (w) => (w ?? 0) + 2)
    else layout.addEdge(a, b, { weight: 2 })
  }
  forceAtlas2.assign(layout, {
    iterations: 400,
    getEdgeWeight: 'weight',
    settings: { ...forceAtlas2.inferSettings(layout), gravity: 0.5, scalingRatio: 6 },
  })
  const community = louvain(layout, { getEdgeWeight: 'weight', rng: rng(7) })

  const degree = new Map<number, number>()
  for (const e of data.edges) {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
  }

  // Lines: communities ranked by size and, like transit lines, named after their busiest
  // station (several lines can share a hub file, so the file alone doesn't tell them apart).
  const members = new Map<number, typeof data.nodes>()
  for (const n of data.nodes) {
    const c = community[String(n.id)]
    members.set(c, [...(members.get(c) ?? []), n])
  }
  const ranked = [...members.entries()].sort((a, b) => b[1].length - a[1].length)
  const lines: Line[] = ranked.map(([c, stations], i) => {
    const hub = stations.reduce((a, b) => ((degree.get(b.id) ?? 0) > (degree.get(a.id) ?? 0) ? b : a))
    return {
      id: c,
      color: LINE_COLORS[i] ?? OTHER_LINE,
      label: displayName(hub),
      hubPath: hub.path,
      size: stations.length,
    }
  })
  const colorOf = new Map(lines.map((l) => [l.id, l.color]))

  // Display graph: stations and track, plus label-only district nodes at each file's centre.
  const graph = new Graph({ type: 'directed' })
  const lineOf = new Map<string, number>()
  for (const n of data.nodes) {
    const key = String(n.id)
    const { x, y } = layout.getNodeAttributes(key)
    const c = community[key]
    lineOf.set(key, c)
    graph.addNode(key, {
      x, y,
      kind: n.kind === 'module' ? 'module' : 'function',
      label: displayName(n),
      line_no: n.start_line,
      path: n.path,
      size: Math.min(3 + Math.sqrt(degree.get(n.id) ?? 0) * 1.6, 11),
      line: colorOf.get(c) ?? OTHER_LINE,
    })
  }
  const stationsIn = new Map<string, number>()
  for (const n of data.nodes) stationsIn.set(n.path, (stationsIn.get(n.path) ?? 0) + 1)
  // landmark rank: 0 = biggest file. Narrow screens label fewer of them.
  const landmarks = new Map([...stationsIn.entries()].sort((a, b) => b[1] - a[1])
    .slice(0, LANDMARKS).map(([p], i) => [p, i]))
  for (const path of files) {
    // Label the file at its busiest station: a real place on the map, not an average of
    // positions that can fall between neighbourhoods.
    let hub = '', best = -1
    graph.forEachNode((node, a) => {
      if (a.path === path && (degree.get(Number(node)) ?? 0) > best) {
        best = degree.get(Number(node)) ?? 0
        hub = node
      }
    })
    const { x, y } = graph.getNodeAttributes(hub)
    graph.addNode(`file:${path}`, {
      x, y, kind: 'file', label: shortPath(path), size: 0.1, path,
      line: OTHER_LINE, landmark: landmarks.get(path) ?? null,
    })
  }
  for (const e of data.edges) {
    const [a, b] = [String(e.source), String(e.target)]
    if (a === b || graph.hasEdge(a, b)) continue
    const same = lineOf.get(a) === lineOf.get(b)
    graph.addDirectedEdge(a, b, {
      via: e.via,
      sameLine: same,
      line: same ? graph.getNodeAttribute(a, 'line') : OTHER_LINE,
    })
  }
  return { graph, lines, lineOf, calls: data.edges.length } // every link, recursion included
}
