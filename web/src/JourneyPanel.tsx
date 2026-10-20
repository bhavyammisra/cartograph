import { RotateCcw, X } from 'lucide-react'
import type { AgentEvent } from './api'
import { describe, explain, steps, type Journey } from './journey'

type Props = {
  question: string
  events: AgentEvent[] // the visible part (all of it, or a replay in progress)
  journey: Journey
  status: 'running' | 'done' | 'error'
  seconds: number | null
  tokens: number | null
  replaying: boolean
  nameOf: (handle: unknown) => string
  placeOf: (id: string) => { path: string; line: number; color: string }
  onPick: (id: number) => void
  onReplay: () => void
  onClose: () => void
}

/** The agent's route as a list: numbered steps, the destination, and why it was chosen. */
export default function JourneyPanel(p: Props) {
  const list = steps(p.events)
  const status =
    p.status === 'running' ? `Working, step ${list.length + 1}`
      : p.status === 'error' ? 'Stopped before an answer'
        : `Arrived in ${p.seconds?.toFixed(0)} s, ${list.length} steps${p.tokens ? `, ${p.tokens.toLocaleString()} tokens` : ''}`
  const arrived = p.status === 'done' && !p.replaying
  const gaveUp = !p.journey.notFound && p.journey.destinations.length === 0

  return (
    <aside className="panel" aria-label="Agent route">
      <header className="sign">
        <span className="sign-bullet route-bullet" aria-hidden />
        <div className="sign-text">
          <h2>{p.question}</h2>
          <p className="sign-where" role="status">{status}</p>
        </div>
        <button type="button" className="icon-button" onClick={p.onClose} aria-label="Close route">
          <X size={18} aria-hidden />
        </button>
      </header>
      <div className="panel-body">
        <ol className="steps" aria-label="Steps">
          {list.map(({ n, event }) => (
            <li key={n} className={event.type === 'error' ? 'step error' : 'step'}>
              <span className="step-no" aria-hidden>{n}</span>
              <span className="step-text">{describe(event, p.nameOf)}</span>
              {event.type === 'tool' && (
                <span className="step-meta">
                  {event.ids.length} function{event.ids.length === 1 ? '' : 's'}, {(event.ms / 1000).toFixed(1)} s
                </span>
              )}
            </li>
          ))}
          {p.status === 'running' && <li className="step pending"><span className="step-no" aria-hidden /> Thinking</li>}
        </ol>

        {arrived && (
          <section className="destination" aria-label="Destination">
            <h3>{p.journey.notFound ? 'Not found' : gaveUp ? 'No answer' : 'Destination'}</h3>
            {p.journey.notFound && <p className="none">The agent reported that this codebase doesn't answer it.</p>}
            {gaveUp && <p className="none">The agent ran out of steps without naming a function. The numbered stops are the closest it got.</p>}
            {p.journey.destinations.map((id) => {
              const place = p.placeOf(id)
              return (
                <div key={id} className="dest">
                  <button type="button" className="dest-name" onClick={() => p.onPick(Number(id))}>
                    <span className="bullet" style={{ background: place.color }} aria-hidden />
                    <span className="conn-name">{p.nameOf(id)}</span>
                    <span className="conn-path">{place.path}:{place.line}</span>
                  </button>
                  <h4>Why this result</h4>
                  <ul className="why">
                    {explain(Number(id), p.events, p.nameOf).map((line) => <li key={line}>{line}</li>)}
                  </ul>
                </div>
              )
            })}
          </section>
        )}

        <div className="journey-foot">
          {p.status === 'done' && (
            <button type="button" className="text-button" onClick={p.onReplay} disabled={p.replaying}>
              <RotateCcw size={14} aria-hidden /> Replay
            </button>
          )}
          <p className="key-note">
            Numbered: stops the agent made. Plain ring: shown to it, not visited. Thick track:
            it followed a call. Thin: it jumped there from a search.
          </p>
        </div>
      </div>
    </aside>
  )
}
