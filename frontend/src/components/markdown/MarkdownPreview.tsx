import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Components } from 'react-markdown'
import Mermaid from './Mermaid'

const components: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    const text = String(children).replace(/\n$/, '')
    if (match?.[1] === 'mermaid') {
      return <Mermaid chart={text} />
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    )
  },
}

interface MarkdownPreviewProps {
  content: string
  className?: string
}

export default function MarkdownPreview({ content, className = '' }: MarkdownPreviewProps) {
  if (!content.trim()) {
    return <p className="text-sm text-ink-3">No documentation yet.</p>
  }
  return (
    <div className={`prose prose-ink max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        // No rehype-raw: raw HTML in docs is not rendered (XSS-safe).
        rehypePlugins={[[rehypeHighlight, { ignoreMissing: true, plainText: ['mermaid'] }]]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
