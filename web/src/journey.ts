// Turns the agent's recorded steps into a route on the map, and explains each answer.
// Everything here is derived from the events alone, so the drawing and the explanation can
// never disagree with what the agent actually did.

import type { AgentEvent } from './api'

/** A step as listed in the Journey panel; `n` is its 1-based number there. */
export type Step = { n: number; event: AgentEvent }

export type Journey = {
  stops: { node: string; n: number }[] // stations the agent went to (read or explored), in order
  considered: Set<string> // stations it was shown but didn't go to
  destinations: string[] // its final answer
  legs: { from: string; to: string; kind: 'call' | 'jump' }[] // track between consecutive stops
  notFound: boolean
}

const fid = (handle: unknown) => /^F?(\d+)$/.exec(String(handle).trim())?.[1] ?? null

export function steps(events: AgentEvent[]): Step[] {
  return events.filter((e) => e.type !== 'done').map((event, i) => ({ n: i + 1, event }))
}

/** `isCall(a, b)` says whether the code graph has a call either way between two stations. */
export function buildJourney(events: AgentEvent[], isCall: (a: string, b: string) => boolean): Journey {
  const stops: Journey['stops'] = []
  const considered = new Set<string>()
  let destinations: string[] = []
  let notFound = false
  const visit = (node: string | null, n: number) => {
    if (node && !stops.some((s) => s.node === node)) stops.push({ node, n })
  }
  for (const { n, event: e } of steps(events)) {
    if (e.type === 'tool') {
      e.ids.forEach((id) => considered.add(String(id)))
      if (e.tool === 'read_code') visit(e.ids[0] !== undefined ? String(e.ids[0]) : null, n)
      if (e.tool === 'graph_neighbors') visit(fid(e.args.function), n)
    } else if (e.type === 'answer') {
      destinations = e.ids.map(String)
    }
  }
  const done = events.find((e) => e.type === 'done')
  if (done?.type === 'done') notFound = done.not_found && done.answer.length === 0

  const path = [...stops.map((s) => s.node), ...destinations.filter((d) => !stops.some((s) => s.node === d))]
  const legs = path.slice(1).map((to, i) => ({
    from: path[i], to, kind: isCall(path[i], to) ? ('call' as const) : ('jump' as const),
  }))
  for (const node of [...path]) considered.delete(node)
  return { stops, considered, destinations, legs, notFound }
}

const TOOL_PHRASE: Record<string, string> = {
  search_meaning: 'meaning search',
  search_keyword: 'keyword search',
  graph_neighbors: 'following calls',
  read_code: 'reading code',
}

/** Plain sentences on how one answer was found, each tied to a numbered step. */
export function explain(id: number, events: AgentEvent[], nameOf: (handle: unknown) => string): string[] {
  const lines: string[] = []
  let found = false
  for (const { n, event: e } of steps(events)) {
    if (e.type === 'tool' && e.ids.includes(id)) {
      const rank = e.ids.indexOf(id) + 1
      if (e.tool === 'read_code') lines.push(`Code read at step ${n}.`)
      else if (e.tool === 'graph_neighbors') {
        const dir = e.args.direction === 'callers' ? 'callers' : 'calls'
        lines.push(`${found ? 'Reached again' : 'Reached'} at step ${n} by following the ${dir} of ${nameOf(e.args.function)}.`)
      } else {
        lines.push(`${found ? 'Also ranked' : 'Found at step ' + n + ' by ' + TOOL_PHRASE[e.tool] + ','} #${rank}${found ? ` by ${TOOL_PHRASE[e.tool]} at step ${n}` : ''} for "${String(e.args.query ?? '')}".`)
      }
      found = true
    }
    if (e.type === 'answer' && e.ids.includes(id)) {
      lines.push(e.from_text ? `Named in the agent's written reply at step ${n} (it never called submit).`
        : `Chosen as the answer at step ${n}.`)
    }
  }
  return lines
}

/** One-line description of a step for the Journey panel. */
export function describe(e: AgentEvent, nameOf: (handle: unknown) => string): string {
  if (e.type === 'tool') {
    if (e.tool === 'search_meaning') return `Meaning search "${e.args.query}"`
    if (e.tool === 'search_keyword') return `Keyword search "${e.args.query}"`
    if (e.tool === 'read_code') return `Read ${nameOf(e.args.function)}`
    if (e.tool === 'graph_neighbors') return `Followed the ${e.args.direction === 'callers' ? 'callers' : 'calls'} of ${nameOf(e.args.function)}`
    return `${e.tool}`
  }
  if (e.type === 'answer') return e.ids.length ? `Arrived${e.from_text ? ' (read from its reply)' : ''}: ${e.ids.map(nameOf).join(', ')}` : 'Reported: not in this codebase'
  if (e.type === 'text') return 'Replied in text instead of a tool; asked to submit'
  if (e.type === 'error') return `Stopped: ${e.text}`
  return ''
}
