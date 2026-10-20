---
name: Cartograph
description: A codebase read like a transit map, for finding where code happens and how it connects.
colors:
  paper: "#f7f6f2"
  panel: "#ffffff"
  ink: "#17191c"
  ink-muted: "#565b62"
  rule: "#dddbd4"
  track-faint: "#e3e1da"
  hover: "#efede7"
  focus: "#17191c"
  paper-dark: "#121417"
  panel-dark: "#1b1e22"
  ink-dark: "#eceae4"
  ink-muted-dark: "#a3a8ae"
  rule-dark: "#2d3137"
  track-faint-dark: "#262a2f"
  focus-dark: "#eceae4"
  line-red: "#d6362c"
  line-green: "#00843d"
  line-blue: "#0b4fa8"
  line-raspberry: "#c2337a"
  line-orange: "#ef6a1a"
  line-plum: "#8c4799"
  line-brown: "#8a5a2b"
  line-teal: "#0098b3"
  line-other: "#8d9196"
  map-grey: "#cfcbc1"
  route-ring: "#17191c"
  route-fill: "#f5c400"
  route-track: "#a87f00"
  map-grey-dark: "#3a3e44"
  route-dark: "#ffd200"
typography:
  title:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  sign:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  label:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.08em"
  code:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: "4px"
  md: "6px"
  sheet: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
components:
  search-input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "36px"
  icon-button:
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    size: "32px"
  list-row-hover:
    backgroundColor: "{colors.hover}"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    width: "440px"
---

# Design System: Cartograph

## Overview

**Creative North Star: "The Transit Map"**

Cartograph shows a codebase the way a metro diagram shows a city: neighbourhoods of code are coloured lines, functions are stations, calls are track. The map is the work area and owns the screen; the interface around it is ink on paper, quiet enough that the line colours carry the meaning. Density is high and calm: small type, tabular numbers, thin rules, no decoration that does not explain the code.

Light and dark both exist and follow the system setting; they are the same map printed on two papers. Anything shown is real data from the index; nothing on screen is illustrative.

**Key Characteristics:**
- Enamel line colours belong to neighbourhoods only, never to controls.
- Stations: a coloured ring around a paper-coloured centre; a file's top-level code is a solid stop; size grows with calls.
- One workhorse grotesk (Archivo) with tabular numerals; JetBrains Mono only for code.
- Semantic zoom: file names are landmarks when zoomed out, function names when zoomed in.
- Two modes: exploring shows the full-colour transit map; picking a function (search or click) turns the map grey and lights its route in yellow, the only yellow on screen.

## Colors

Ink and paper for the interface, eight enamel colours for the lines.

### Primary
- **Signal Line Colours** (line-red, line-green, line-blue, line-raspberry, line-orange, line-plum, line-brown, line-teal): one per neighbourhood, assigned by size, largest first. Used for station rings, same-line track, line bullets in lists and the station sign. Smaller neighbourhoods share **Siding Grey** (line-other).

### Secondary
- **Route Yellow** (route-fill and route-track on light paper; route-dark on dark): the route only. Light: yellow station fill with a Print Ink ring (route-ring) and deep-gold track (3.4:1 against paper, because thin bright yellow fails contrast on paper). Dark: signal yellow ring and track.
- **Map Grey** (map-grey / map-grey-dark): every station off the route while a route is shown.

### Neutral
- **Survey Paper** (paper / paper-dark): the map ground and page background.
- **Sign Board** (panel / panel-dark): top bar, key, results list and side panel.
- **Print Ink** (ink / ink-dark): text, controls and icons.
- **Pencil** (ink-muted / ink-muted-dark): paths, counts, secondary text.
- **Hairline** (rule / rule-dark): borders and dividers, 1px.
- **Faded Track** (track-faint / track-faint-dark): cross-line track and dimmed stations.
- **Ink Ring** (focus / focus-dark): focus rings, in ink so focus never reads as a line.

### Named Rules
**The Lines Are Not Buttons Rule.** Line colours mark neighbourhoods. Controls, links and focus never use them, so a colour on screen always means "this code belongs here".

**The Yellow Route Rule.** Yellow means one thing: where you are going. It appears only on a picked station, its direct connections and the track between them (and, later, the agent's route). No line, control or label is ever yellow or amber.

**The Fade, Don't Delete Rule.** Showing a route turns everything else to Map Grey; focusing a line fades the rest to Faded Track. Nothing disappears from the map.

## Typography

**Display / UI Font:** Archivo Variable (self-hosted, with system-ui fallback)
**Code Font:** JetBrains Mono (self-hosted)

**Character:** A plain, slightly wide grotesk in the tradition of transit signage; rank comes from weight and case, not from many sizes.

### Hierarchy
- **Title** (700, 20px, 1.2): the function name on the station sign.
- **Sign** (700, 17px): the product name in the top bar.
- **Body** (400, 14px, 1.45, tabular numerals): results, connections, key entries.
- **Label** (700, 12px, 0.08em, uppercase): section names (Lines, Called by, Calls) and the repository name.
- **Code** (400, 12px, 1.6): source in the panel, with line numbers.

### Named Rules
**The Four Sizes Rule.** 12, 14, 17 and 20px are the whole scale. A new level is a weight or case change, not a new size.

## Layout

A top bar (brand, real counts, search) over a full-bleed map. The lines key floats bottom-left (280px). Selecting a station opens a 440px panel on the right and the map narrows to the space beside it. Under 760px the search moves to its own row, counts wrap under the brand, the key starts collapsed, and the panel becomes a bottom sheet over 58% of the screen while the map shrinks to the area above it. Spacing steps: 4, 8 and 16px; panels pad 16px.

## Elevation & Depth

Flat. Surfaces separate by tone (Sign Board over Survey Paper) and 1px hairlines. Shadows appear only on things that float over the map: the results list and the phone bottom sheet (`0 8px 24px rgb(0 0 0 / 0.12)`).

### Named Rules
**The Paper Map Rule.** Depth comes from tone and hairlines. A shadow means "this floats over the map", nothing else.

## Shapes

Small, practical corners: 4px for list rows, 6px for inputs, buttons and floating panels, 12px only for the top of the phone bottom sheet. Stations and line bullets are circles; key swatches are short rounded bars, like line segments.

## Components

### Search
- **Style:** 36px field on Survey Paper with a hairline border and 6px corners; search icon left, a `/` key hint right.
- **Focus:** 2px Ink Ring.
- **Results:** a floating list of rows (line bullet, name in 600, file:line in Pencil); the active row is tinted Hover. Arrow keys move, Enter flies the map to the station.

### Station Sign (signature)
The panel header: a 22px line bullet, the function name in Title, then file and line range in Pencil, and a 32px close button. Below it the code, then **Called by** and **Calls** as transfer lists: each row a line bullet, the name and file:line, clickable to change trains.

### Lines Key
A floating card listing lines by size: a coloured bar, the line's busiest station, its station count, and its hub file beneath. Rows toggle a line focus (`aria-pressed`). A closing note explains rings, solid stops and size.

### Map Labels
Function labels sit right of their station; file landmarks sit centred above their busiest station. Both carry a 4px halo in the map colour so they stay legible over track.

## Do's and Don'ts

### Do:
- **Do** name a line after its busiest station and show that station's file beneath.
- **Do** switch the map to grey with a yellow route when a function is picked, and restore colours when it is closed.
- **Do** keep every number on screen traceable to the index or a measurement.
- **Do** give every map label a halo in the map colour.
- **Do** reach every function by keyboard through search or the connection lists.

### Don't:
- **Don't** use a line colour on a button, link or focus state.
- **Don't** use yellow or amber anywhere except the route.
- **Don't** add type sizes beyond the four in the scale.
- **Don't** add shadows to surfaces that don't float over the map.
- **Don't** use purple gradients, pill-shaped buttons, emoji icons, invented metrics or filler copy (owner's standing rules).
