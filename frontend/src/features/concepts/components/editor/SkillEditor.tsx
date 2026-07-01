// frontend/src/features/concepts/components/editor/SkillEditor.tsx
import Editor, { type OnMount } from "@monaco-editor/react";
import { forwardRef, useImperativeHandle, useRef } from "react";
import { tokens } from "@/app/theme/tokens";
import type { Sel, Transform } from "@/features/concepts/lib/markdownTransforms";
import { filterCommands } from "@/features/concepts/lib/slashCommands";

export interface SkillEditorHandle {
  applyTransform(t: Transform): void;
}

type MonacoEditor = Parameters<OnMount>[0];
type Monaco = Parameters<OnMount>[1];

export const SkillEditor = forwardRef<SkillEditorHandle, {
  value: string;
  onChange: (v: string) => void;
}>(function SkillEditor({ value, onChange }, ref) {
  const editorRef = useRef<MonacoEditor | null>(null);

  function offsetsFromEditor(ed: MonacoEditor): Sel {
    const model = ed.getModel();
    const selection = ed.getSelection();
    if (!model || !selection) return { start: 0, end: value.length };
    return {
      start: model.getOffsetAt({ lineNumber: selection.startLineNumber, column: selection.startColumn }),
      end: model.getOffsetAt({ lineNumber: selection.endLineNumber, column: selection.endColumn }),
    };
  }

  useImperativeHandle(ref, () => ({
    applyTransform(t: Transform) {
      const ed = editorRef.current;
      // Fallback when Monaco is not mounted (tests / first paint): whole-doc selection.
      const sel: Sel = ed ? offsetsFromEditor(ed) : { start: 0, end: value.length };
      const result = t(value, sel);
      onChange(result.text);
      if (ed) {
        const model = ed.getModel();
        if (model) {
          const startPos = model.getPositionAt(result.selection.start);
          const endPos = model.getPositionAt(result.selection.end);
          ed.setSelection({
            startLineNumber: startPos.lineNumber,
            startColumn: startPos.column,
            endLineNumber: endPos.lineNumber,
            endColumn: endPos.column,
          });
          ed.focus();
        }
      }
    },
  }));

  const handleMount: OnMount = (editor, monaco: Monaco) => {
    editorRef.current = editor;
    registerSlash(monaco);
  };

  return (
    <Editor
      height="100%"
      defaultLanguage="markdown"
      value={value}
      onChange={(v) => onChange(v ?? "")}
      onMount={handleMount}
      options={{
        wordWrap: "on",
        minimap: { enabled: false },
        fontFamily: tokens.font.mono,
        fontSize: 13,
        lineNumbers: "off",
        scrollBeyondLastLine: false,
        padding: { top: 12 },
      }}
    />
  );
});

// Register the `/` slash menu as a Monaco completion provider (idempotent).
let slashRegistered = false;
function registerSlash(monaco: Monaco) {
  if (slashRegistered) return;
  slashRegistered = true;
  monaco.languages.registerCompletionItemProvider("markdown", {
    triggerCharacters: ["/"],
    provideCompletionItems(model, position) {
      const line = model.getLineContent(position.lineNumber).slice(0, position.column - 1);
      const match = /\/(\w*)$/.exec(line);
      if (!match) return { suggestions: [] };
      const query = match[1];
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn - 1, // include the leading "/"
        endColumn: word.endColumn,
      };
      const suggestions = filterCommands(query).map((cmd) => {
        const applied = cmd.apply("", { start: 0, end: 0 });
        return {
          label: `/${cmd.id}`,
          kind: monaco.languages.CompletionItemKind.Snippet,
          detail: cmd.detail,
          documentation: cmd.label,
          insertText: applied.text,
          range,
        };
      });
      return { suggestions };
    },
  });
}

export default SkillEditor;
