import { useEffect, useRef, useState } from 'react'

let mermaidPromise: Promise<typeof import('mermaid').default> | null = null

// Lazy-load mermaid once and code-split it out of the main bundle. It is only
// fetched the first time a diagram actually needs to render.
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then((mod) => {
      const mermaid = mod.default
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'neutral',
        fontFamily: 'Geist Sans, system-ui, sans-serif',
      })
      return mermaid
    })
  }
  return mermaidPromise
}

let counter = 0

interface MermaidProps {
  chart: string
}

export default function Mermaid({ chart }: MermaidProps) {
  const [svg, setSvg] = useState<string>('')
  const [error, setError] = useState<string>('')
  const idRef = useRef(`mermaid-${(counter += 1)}`)

  useEffect(() => {
    let cancelled = false
    setError('')
    loadMermaid()
      .then((mermaid) => mermaid.render(idRef.current, chart))
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSvg('')
          setError(err instanceof Error ? err.message : 'Failed to render diagram')
        }
      })
    return () => {
      cancelled = true
    }
  }, [chart])

  if (error) {
    return (
      <div className="my-4 overflow-hidden rounded-lg border border-line">
        <p className="border-b border-line bg-canvas px-3 py-2 text-xs font-medium text-bad">
          Diagram error: {error}
        </p>
        <pre className="overflow-x-auto bg-canvas p-3 text-xs text-ink-2">
          <code>{chart}</code>
        </pre>
      </div>
    )
  }

  if (!svg) {
    return (
      <div className="my-4 h-24 animate-pulse rounded-lg border border-line bg-canvas" />
    )
  }

  return (
    <div
      className="my-4 flex justify-center overflow-x-auto rounded-lg border border-line bg-surface p-4"
      // mermaid output is sanitized at securityLevel 'strict'
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
