// frontend/src/features/concepts/lib/sanitizeSchema.ts
import { defaultSchema } from "rehype-sanitize";
import type { Root, Element } from "hast";
import { visit, SKIP } from "unist-util-visit";

// Hosts whose iframes we allow (embeds). Everything else is dropped.
export const ALLOWED_IFRAME_HOSTS = [
  "www.youtube.com",
  "youtube.com",
  "player.vimeo.com",
];

// Extend the GitHub-safe default with presentational tags + iframe embeds.
export const PREVIEW_SANITIZE_SCHEMA = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "details", "summary", "iframe", "figure", "figcaption"],
  attributes: {
    ...defaultSchema.attributes,
    "*": [...(defaultSchema.attributes?.["*"] ?? []), "className"],
    iframe: ["src", "width", "height", "allow", "allowfullscreen", "title", "frameborder"],
  },
} as typeof defaultSchema;

// Runs AFTER sanitize: drop any iframe whose src host is not allow-listed.
export function rehypeIframeAllowlist() {
  return (tree: Root) => {
    visit(tree, "element", (node: Element, index, parent) => {
      if (node.tagName !== "iframe" || !parent || index === undefined) return;
      const src = String(node.properties?.src ?? "");
      let host = "";
      try {
        host = new URL(src).host;
      } catch {
        host = "";
      }
      if (!ALLOWED_IFRAME_HOSTS.includes(host)) {
        (parent.children as unknown[]).splice(index, 1);
        return [SKIP, index];
      }
    });
  };
}
