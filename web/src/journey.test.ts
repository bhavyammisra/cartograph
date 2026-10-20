// Run with: npm test  (Node's built-in test runner; Node strips the TypeScript types)
import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { AgentEvent } from './api.ts'
import { buildJourney, explain } from './journey.ts'

// A real-shaped run: search, read a result, follow its callers, answer.
const EVENTS: AgentEvent[] = [
  { type: 'tool', step: 0, tool: 'search_meaning', args: { query: 'delete cookie' }, ids: [5, 9, 7], ms: 10 },
  { type: 'tool', step: 1, tool: 'read_code', args: { function: 'F5' }, ids: [5], ms: 5 },
  { type: 'tool', step: 2, tool: 'graph_neighbors', args: { function: 'F5', direction: 'callers' }, ids: [8], ms: 5 },
  { type: 'answer', step: 3, ids: [5, 8] },
  { type: 'done', answer: [5, 8], not_found: false, ranked: [5, 8, 9, 7], tokens: 100 },
]
const isCall = (a: string, b: string) => (a === '8' && b === '5') || (a === '5' && b === '8')
const name = (h: unknown) => `fn${String(h).replace('F', '')}`

test('stops, considered, destinations and legs come from the steps', () => {
  const j = buildJourney(EVENTS, isCall)
  assert.deepEqual(j.stops, [{ node: '5', n: 2 }]) // read at step 2; exploring it again adds no stop
  assert.deepEqual(j.destinations, ['5', '8'])
  assert.deepEqual([...j.considered].sort(), ['7', '9']) // seen, never visited
  assert.deepEqual(j.legs, [{ from: '5', to: '8', kind: 'call' }])
  assert.equal(j.notFound, false)
})

test('a search jump between unrelated stations is a jump, not a call', () => {
  const j = buildJourney(EVENTS, () => false)
  assert.equal(j.legs[0].kind, 'jump')
})

test('explanations cite the numbered steps', () => {
  assert.deepEqual(explain(5, EVENTS, name), [
    'Found at step 1 by meaning search, #1 for "delete cookie".',
    'Code read at step 2.',
    'Chosen as the answer at step 4.',
  ])
  assert.deepEqual(explain(8, EVENTS, name), [
    'Reached at step 3 by following the callers of fn5.',
    'Chosen as the answer at step 4.',
  ])
})

test('an answer read from prose says so', () => {
  const events: AgentEvent[] = [{ type: 'answer', step: 0, ids: [5], from_text: true }]
  assert.deepEqual(explain(5, events, name), ["Named in the agent's written reply at step 1 (it never called submit)."])
})

test('an empty answer with not_found is reported as not found', () => {
  const j = buildJourney([{ type: 'answer', step: 0, ids: [] },
                          { type: 'done', answer: [], not_found: true, ranked: [], tokens: 1 }], isCall)
  assert.equal(j.notFound, true)
  assert.deepEqual(j.destinations, [])
})
