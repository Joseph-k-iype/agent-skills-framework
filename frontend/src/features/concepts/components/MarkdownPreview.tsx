import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import mermaid from "mermaid";
import { PREVIEW_SANITIZE_SCHEMA, rehypeIframeAllowlist } from "../lib/sanitizeSchema";

let initialized = false;
function ensureInit() {
  if (!initialized) {
    mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
    initialized = true;
  }
}

let seq = 0;

/** Renders one mermaid diagram. Re-renders when the chart source changes. */
function Mermaid({ chart }: { chart: string }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`mermaid-${(seq += 1)}`);

  useEffect(() => {
    let active = true;
    ensureInit();
    mermaid
      .render(idRef.current, chart)
      .then((res) => {
        if (active) {
          setSvg(res.svg);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(e instanceof Error ? e.message : "Invalid diagram");
      });
    return () => {
      active = false;
    };
  }, [chart]);

  if (error) {
    return (
      <pre data-testid="mermaid-error" style={{ color: "#b00", whiteSpace: "pre-wrap" }}>
        Diagram error: {error}
      </pre>
    );
  }
  return <div data-testid="mermaid" dangerouslySetInnerHTML={{ __html: svg }} />;
}

/** Markdown renderer with GitHub-flavored markdown and live mermaid diagrams. */
export function MarkdownPreview({ source }: { source: string }) {
  return (
    <div className="markdown-preview">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, PREVIEW_SANITIZE_SCHEMA], rehypeIframeAllowlist]}
        components={{
          code(props) {
            const { className, children } = props as {
              className?: string;
              children?: React.ReactNode;
            };
            const match = /language-(\w+)/.exec(className ?? "");
            if (match?.[1] === "mermaid") {
              return <Mermaid chart={String(children).trim()} />;
            }
            return <code className={className}>{children}</code>;
          },
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownPreview;
