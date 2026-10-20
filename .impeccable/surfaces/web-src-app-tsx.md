---
version: 1
slug: "web-src-app-tsx"
primary_target: "web/src/App.tsx"
related_targets: []
---

# Surface: the code map (web/src)

Mode: Operate. Audience: developers exploring a JS codebase, and demo viewers (equal weight). Accessibility: WCAG 2.1 AA.
Task: see how the codebase connects, find a function (search or browse), read its code, follow its callers and callees. Data: /api/health, /api/graph, /api/functions/{id}, /api/search. Phase 8 adds the agent route; Phase 9 the impact ripple.

## Direction contract

THESIS: The codebase read like a metro map: neighbourhoods are lines, functions are stations, calls are track. Refuses the category default of glowing nodes on a navy canvas with a generic sidebar.

OWN-WORLD: Off-white (light) or near-black (dark) ground; enamel line colours (signal red, green, blue, raspberry, orange, plum, brown, teal) only for neighbourhoods, never for controls; Route Yellow reserved for where you are going (raise from Terminal Wayfinding, chosen by Bhavyam): picking a function greys the map and lights its route; stations are white-filled dots with a coloured ring, hubs are interchange rings; ink for text and controls; one workhorse grotesk, tabular numerals, few sizes, rank by weight.

STORY: The viewer understands at a glance that colours are neighbourhoods and lines are calls; the developer searches, lands on a station, reads its code, and changes trains to a caller or callee.

FIRST VIEWPORT: Top bar (name, repo, real function and call counts, search). The map fills the rest. A Lines key bottom-left. Selecting a station opens a right panel (bottom sheet on phones) headed like a station sign: line bullet, function name, file:line, then the code, then Connections as transfer lists. While the panel is open the map is grey except the yellow route.

FORM: Transit Diagram, position 1 on the ordered list (the IMPECCABLE PICK, chosen by the user). seed:fb63b0cb5be10a0d. Signature move: stations and lines; picking a function shows its route in yellow on a grey map; in Phase 8 the agent's search is drawn as a yellow route with stops. Raised line: yellow belongs only to the path (from Terminal Wayfinding).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved
- Octilinear layout is out of scope (it can misstate connections); force layout, transit rendering.
- Agent route styling (Phase 8) and impact ripple (Phase 9).
