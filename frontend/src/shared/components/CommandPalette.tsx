import { Input, Modal, Typography } from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { usePublicMarketplace } from "@/features/marketplace/api/publicMarketplaceApi";

const MAX_RESULTS = 8;
const DEBOUNCE_MS = 200;

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * `⌘K` / `Ctrl-K` search overlay for the public marketplace.
 * Owns its own global shortcut listener so it can be mounted once in
 * `PublicLayout`; the open/close state is still controlled by the parent
 * so other affordances (e.g. the search pill) can open it too.
 */
export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const id = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(true);
      } else if (e.key === "Escape") {
        onOpenChange(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setDebouncedQuery("");
    }
  }, [open]);

  const { data: results, isFetching } = usePublicMarketplace(
    debouncedQuery,
    undefined,
    undefined,
    "uses",
  );

  function handleSelect(id: string) {
    onOpenChange(false);
    navigate(`/marketplace/${id}`);
  }

  return (
    <Modal
      open={open}
      onCancel={() => onOpenChange(false)}
      footer={null}
      closable={false}
      width={560}
      styles={{ body: { padding: 0 } }}
    >
      <div style={{ padding: tokens.space * 2 }}>
        <Input
          autoFocus
          size="large"
          placeholder="Search skills, datasets, prompts…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ borderRadius: tokens.radius }}
        />
      </div>
      {debouncedQuery && (
        <div style={{ borderTop: `1px solid ${tokens.color.line}`, maxHeight: 360, overflowY: "auto" }}>
          {isFetching && (
            <div style={{ padding: tokens.space * 2, color: tokens.color.ink3, fontSize: 13 }}>Searching…</div>
          )}
          {!isFetching && results?.length === 0 && (
            <div style={{ padding: tokens.space * 2, color: tokens.color.ink3, fontSize: 13 }}>
              No results for &ldquo;{debouncedQuery}&rdquo;
            </div>
          )}
          {!isFetching &&
            results?.slice(0, MAX_RESULTS).map((r) => (
              <div
                key={r.id}
                onClick={() => handleSelect(r.id)}
                style={{
                  padding: `${tokens.space * 1.5}px ${tokens.space * 2}px`,
                  cursor: "pointer",
                  borderBottom: `1px solid ${tokens.color.line}`,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = tokens.color.canvas)}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ display: "flex", alignItems: "baseline", gap: tokens.space }}>
                  <Typography.Text strong style={{ color: tokens.color.ink }}>
                    {r.title}
                  </Typography.Text>
                  {r.type && (
                    <Typography.Text style={{ color: tokens.color.accent, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      {r.type}
                    </Typography.Text>
                  )}
                </div>
                {r.summary && (
                  <Typography.Text
                    style={{
                      display: "block",
                      color: tokens.color.ink2,
                      fontSize: 13,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {r.summary}
                  </Typography.Text>
                )}
              </div>
            ))}
        </div>
      )}
    </Modal>
  );
}
