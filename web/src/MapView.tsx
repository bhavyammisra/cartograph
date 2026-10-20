import { createNodeBorderProgram } from '@sigma/node-border'
import { useEffect, useRef } from 'react'
import Sigma from 'sigma'
import type { NodeDisplayData, PartialButFor } from 'sigma/types'
import type { CodeMap } from './buildGraph'

type Props = {
  map: CodeMap
  selected: string | null
  focusLine: number | null
  onSelect: (node: string | null) => void
  flyTo: { node: string; nonce: number } | null
}

type Colors = { bg: string; ink: string; muted: string; faint: string; station: string; panel: string }

function readColors(): Colors {
  const css = getComputedStyle(document.documentElement)
  const v = (name: string) => css.getPropertyValue(name).trim()
  return {
    bg: v('--map-bg'), ink: v('--ink'), muted: v('--ink-muted'), faint: v('--track-faint'),
    station: v('--station'), panel: v('--panel'),
  }
}

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Stations: a coloured ring around a filled centre; a file's top-level code is a solid stop.
const StationProgram = createNodeBorderProgram({
  borders: [
    { size: { attribute: 'ringSize', defaultValue: 0.38 }, color: { attribute: 'ringColor' } },
    { size: { fill: true }, color: { attribute: 'fillColor' } },
  ],
})

export default function MapView({ map, selected, focusLine, onSelect, flyTo }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const sigma = useRef<Sigma | null>(null)
  // Sigma's reducers read this on every frame; React state would re-create the renderer.
  const state = useRef({
    selected, focusLine, hovered: null as string | null, colors: readColors(), ratio: 1,
    landmarks: 12, // how many file labels fit; set from the map's width
  })

  useEffect(() => {
    const { graph, lineOf } = map
    const s = state.current

    const drawLabel = (
      ctx: CanvasRenderingContext2D,
      data: PartialButFor<NodeDisplayData, 'x' | 'y' | 'size' | 'label' | 'color'>,
    ) => {
      if (!data.label) return
      const district = (data as { kind?: string }).kind === 'file'
      ctx.font = district ? `600 12px "Archivo Variable", sans-serif` : `400 12px "Archivo Variable", sans-serif`
      ctx.textBaseline = 'middle'
      // A district name sits above its hub station; a station name to the right of its dot.
      const [x, y] = district ? [data.x, data.y - 16] : [data.x + data.size + 4, data.y]
      ctx.textAlign = district ? 'center' : 'left'
      // Halo in the map colour, as printed maps do, so labels stay legible over track.
      ctx.lineWidth = 4
      ctx.lineJoin = 'round'
      ctx.strokeStyle = s.colors.bg
      ctx.strokeText(data.label, x, y)
      ctx.fillStyle = district ? s.colors.muted : s.colors.ink
      ctx.fillText(data.label, x, y)
      ctx.textAlign = 'left'
    }
    // Hover: the label on a small plate in the panel colour, so it reads on light and dark.
    const drawHover = (
      ctx: CanvasRenderingContext2D,
      data: PartialButFor<NodeDisplayData, 'x' | 'y' | 'size' | 'label' | 'color'>,
    ) => {
      if (!data.label) return
      ctx.font = `600 12px "Archivo Variable", sans-serif`
      const w = ctx.measureText(data.label).width
      ctx.fillStyle = s.colors.panel
      ctx.beginPath()
      ctx.roundRect(data.x + data.size + 1, data.y - 11, w + 10, 22, 4)
      ctx.fill()
      ctx.fillStyle = s.colors.ink
      ctx.textBaseline = 'middle'
      ctx.fillText(data.label, data.x + data.size + 6, data.y)
    }

    const renderer: Sigma = new Sigma(graph, container.current!, {
      defaultNodeType: 'station',
      nodeProgramClasses: { station: StationProgram },
      labelRenderedSizeThreshold: 7,
      labelDensity: 0.6,
      labelGridCellSize: 90,
      defaultDrawNodeLabel: drawLabel,
      defaultDrawNodeHover: drawHover,
      zIndex: true,
      minCameraRatio: 0.05,
      maxCameraRatio: 3,
      // Extra keys (ringColor, fillColor, ringSize) feed the station program's attributes.
      nodeReducer: (node, a): Partial<NodeDisplayData> & Record<string, unknown> => {
        const c = s.colors
        const zoomedOut = s.ratio > 0.45 // camera zoom; 1 = whole map in view
        // Semantic zoom: file names are the landmarks when zoomed out, function names when in.
        if (a.kind === 'file') {
          const show = zoomedOut && a.landmark !== null && a.landmark < s.landmarks
          return { ...a, hidden: !show, forceLabel: show, color: c.bg, zIndex: 3,
                   fillColor: c.bg, ringColor: c.bg, ringSize: 0 }
        }
        const focus = s.selected ?? s.hovered
        const near = focus === node || (focus !== null && graph.areNeighbors(focus, node))
        const onLine = s.focusLine === null || lineOf.get(node) === s.focusLine
        const dim = (focus !== null && !near) || (focus === null && !onLine)
        const solid = a.kind === 'module'
        return {
          ...a,
          label: (zoomedOut && !near) || dim ? null : a.label, // dimmed stations stay unnamed
          // Only the focused station forces its label; neighbours go through Sigma's
          // collision grid so their labels never stack on each other.
          forceLabel: focus === node,
          zIndex: near ? 2 : 1,
          color: a.line,
          ringColor: dim ? c.faint : a.line,
          fillColor: dim ? c.bg : solid ? a.line : c.station,
          size: focus === node ? a.size * 1.5 : a.size,
        }
      },
      edgeReducer: (edge, a) => {
        const c = s.colors
        const [src, dst] = graph.extremities(edge)
        const focus = s.selected ?? s.hovered
        if (focus !== null) {
          const touches = src === focus || dst === focus
          return { ...a, color: touches ? a.line : c.faint, size: touches ? 2.2 : 0.5,
                   zIndex: touches ? 1 : 0 }
        }
        if (s.focusLine !== null) {
          const on = lineOf.get(src) === s.focusLine && lineOf.get(dst) === s.focusLine
          return { ...a, color: on ? a.line : c.faint, size: on ? 2 : 0.5 }
        }
        return { ...a, color: a.sameLine ? a.line : c.faint, size: a.sameLine ? 1.6 : 0.7 }
      },
    })
    sigma.current = renderer
    s.landmarks = renderer.getDimensions().width < 600 ? 5 : 12
    // Sigma only listens for window resizes; the panel opening also resizes the map.
    const resized = new ResizeObserver(() => renderer.resize())
    resized.observe(container.current!)

    renderer.on('clickNode', ({ node }: { node: string }) => {
      if (graph.getNodeAttribute(node, 'kind') !== 'file') onSelect(node)
    })
    renderer.on('clickStage', () => onSelect(null))
    renderer.on('enterNode', ({ node }: { node: string }) => {
      s.hovered = node
      renderer.refresh({ skipIndexation: true })
    })
    renderer.on('leaveNode', () => { s.hovered = null; renderer.refresh({ skipIndexation: true }) })
    // Labels switch between files and functions as the zoom crosses the threshold.
    renderer.getCamera().on('updated', ({ ratio }) => {
      s.ratio = ratio
      renderer.refresh({ skipIndexation: true })
    })

    // Light/dark follows the system; WebGL colours are re-read when it flips.
    const scheme = window.matchMedia('(prefers-color-scheme: dark)')
    const recolor = () => { s.colors = readColors(); renderer.refresh() }
    scheme.addEventListener('change', recolor)
    return () => {
      resized.disconnect()
      scheme.removeEventListener('change', recolor)
      renderer.kill()
      sigma.current = null
    }
  }, [map, onSelect])

  useEffect(() => {
    state.current.selected = selected
    state.current.focusLine = focusLine
    sigma.current?.refresh({ skipIndexation: true })
  }, [selected, focusLine])

  useEffect(() => {
    const r = sigma.current
    if (!r || !flyTo) return
    const pos = r.getNodeDisplayData(flyTo.node)
    if (pos) r.getCamera().animate({ x: pos.x, y: pos.y, ratio: 0.18 },
                                   { duration: reducedMotion() ? 0 : 600, easing: 'quadraticOut' })
  }, [flyTo])

  return (
    <div
      ref={container}
      className="map"
      role="img"
      aria-label="Call graph map. Each dot is a function, each line a call, colours are neighbourhoods of code that call each other. Use search or the lists to reach any function by keyboard."
    />
  )
}
