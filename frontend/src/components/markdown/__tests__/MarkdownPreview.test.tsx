import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MarkdownPreview from '../MarkdownPreview'

// Mock the Mermaid component so the test never loads the heavy mermaid module;
// it just echoes the chart source into a recognizable element.
vi.mock('../Mermaid', () => ({
  default: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>,
}))

describe('MarkdownPreview', () => {
  it('renders markdown headings, bold, and lists', () => {
    render(<MarkdownPreview content={'# Hello\n\nSome **bold** text\n\n- one\n- two'} />)
    expect(screen.getByRole('heading', { name: 'Hello' })).toBeInTheDocument()
    expect(screen.getByText('bold')).toBeInTheDocument()
    expect(screen.getByText('one')).toBeInTheDocument()
    expect(screen.getByText('two')).toBeInTheDocument()
  })

  it('routes a ```mermaid fence to the Mermaid component', () => {
    render(<MarkdownPreview content={'```mermaid\ngraph TD\nA-->B\n```'} />)
    const node = screen.getByTestId('mermaid')
    expect(node).toBeInTheDocument()
    expect(node.textContent).toContain('graph TD')
    expect(node.textContent).toContain('A-->B')
  })

  it('does not route a non-mermaid code fence to Mermaid', () => {
    render(<MarkdownPreview content={'```python\nprint("hi")\n```'} />)
    expect(screen.queryByTestId('mermaid')).not.toBeInTheDocument()
    expect(screen.getByText(/print/)).toBeInTheDocument()
  })

  it('shows a placeholder when empty', () => {
    render(<MarkdownPreview content={'   '} />)
    expect(screen.getByText('No documentation yet.')).toBeInTheDocument()
  })
})
