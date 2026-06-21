import { useState } from 'react'
import Editor from '@monaco-editor/react'
import { Eye, Pencil } from 'lucide-react'
import MarkdownPreview from './MarkdownPreview'

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  height?: string
  readOnly?: boolean
}

export default function MarkdownEditor({
  value,
  onChange,
  height = '420px',
  readOnly = false,
}: MarkdownEditorProps) {
  const [tab, setTab] = useState<'write' | 'preview'>('write')

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="flex items-center gap-1 border-b border-line px-2">
        <button
          type="button"
          onClick={() => setTab('write')}
          className={
            tab === 'write'
              ? 'tab-active flex items-center gap-2'
              : 'tab flex items-center gap-2'
          }
        >
          <Pencil size={14} /> Write
        </button>
        <button
          type="button"
          onClick={() => setTab('preview')}
          className={
            tab === 'preview'
              ? 'tab-active flex items-center gap-2'
              : 'tab flex items-center gap-2'
          }
        >
          <Eye size={14} /> Preview
        </button>
      </div>

      {tab === 'write' ? (
        <Editor
          height={height}
          defaultLanguage="markdown"
          theme="light"
          value={value}
          onChange={(v) => onChange(v ?? '')}
          options={{
            readOnly,
            minimap: { enabled: false },
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: 'off',
            padding: { top: 12, bottom: 12 },
          }}
        />
      ) : (
        <div className="overflow-y-auto p-5" style={{ height }}>
          <MarkdownPreview content={value} />
        </div>
      )}
    </div>
  )
}
