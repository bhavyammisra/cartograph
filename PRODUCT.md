# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, weighted equally (confirmed 2026-10-20):
- **Developers** exploring an unfamiliar JavaScript/TypeScript codebase on their own machine. Job: find where something happens and how code connects, then read the exact function.
- **Demo viewers** (recruiters, interviewers) watching Cartograph run for the first time. Job: understand within seconds what the map shows and that the results are real and measured.

## Product Purpose

Cartograph answers plain-English questions about a JS/TS codebase with exact files and line ranges. It indexes code into a call graph, keyword and meaning search, and lets an AI agent search it. The web map makes that index visible: the codebase as a navigable graph, a code panel, search, and (from Phase 8) a replay of the agent's search path. Success: a developer reaches the right function faster than with grep; a viewer understands the system from one look.

## Positioning

The map is a window into a measured engine, not decoration: every dot is a real function, every line a real call with a recorded source (tree-sitter rule or Jelly), and accuracy numbers come from a published evaluation. Differentiators: showing the agent's search path on the code map, and "why this result" provenance.

## Operating Context

- Runs locally: `cartograph serve <repo>` on 127.0.0.1:8000; the web app on the Vite dev server (port 5173) proxies `/api`. Source code never leaves the machine.
- Data: `/api/graph`, `/api/functions/{id}`, `/api/search`, `/api/impact/{id}`, `/api/ask` (SSE).
- Development target: Express (325 functions, 308 call edges). Later: larger repositories (thousands of functions).
- Used on a laptop screen; must also work at phone width (demo links get opened on phones).

## Capabilities and Constraints

- Stack (existing): React + TypeScript + Vite; Sigma.js (WebGL) + graphology for the graph.
- Every number shown must come from the index or measured results. No invented stats.
- Standing rules from the owner: no purple gradients, no pill-shaped buttons, no emoji icons, no fake metrics, reviews or counters, no filler or AI-slop copy, no AI-generated imagery, no gimmicky scroll or cursor animations, no em dashes in copy.
- Undecided: hosted demo design (Phase 13), agent-trace visuals (Phase 8), impact ripple visuals (Phase 9).

## Brand Commitments

- Name: Cartograph ("it maps code"). Existing favicon: three connected nodes (`web/public/favicon.svg`).
- No other visual identity exists yet.

## Evidence on Hand

- Measured results in `README.md`, `docs/LEARNING_LOG.md`, `eval/express/` (BM25, hybrid, agent vs grep agent, call-graph accuracy vs Jelly).
- No users, testimonials, or adoption numbers exist; never fabricate them.

## Product Principles

1. Truth on screen: anything displayed traces back to the index or a measurement.
2. Code is the destination: every view leads to exact file + line, readable in place.
3. Legible at a glance, precise on demand: structure first for viewers, detail for developers.
4. Local and private by default.

## Accessibility & Inclusion

WCAG 2.1 AA (confirmed 2026-10-20): contrast, full keyboard operation (search, results, panel, map focus), screen-reader labels, and `prefers-reduced-motion` respected. The WebGL canvas needs keyboard and text alternatives (search and lists reach every function).
