// frontend/src/features/concepts/lib/markdownTransforms.ts
export type Sel = { start: number; end: number };
export type TransformResult = { text: string; selection: Sel };
export type Transform = (text: string, sel: Sel) => TransformResult;

function replaceRange(text: string, start: number, end: number, insert: string): string {
  return text.slice(0, start) + insert + text.slice(end);
}

// Wrap/unwrap the selection with the same marker on both sides.
function toggleWrap(marker: string): Transform {
  return (text, sel) => {
    const before = text.slice(sel.start - marker.length, sel.start);
    const after = text.slice(sel.end, sel.end + marker.length);
    if (before === marker && after === marker) {
      // Unwrap: drop the surrounding markers.
      const stripped =
        text.slice(0, sel.start - marker.length) +
        text.slice(sel.start, sel.end) +
        text.slice(sel.end + marker.length);
      return {
        text: stripped,
        selection: { start: sel.start - marker.length, end: sel.end - marker.length },
      };
    }
    const selected = text.slice(sel.start, sel.end);
    const wrapped = `${marker}${selected}${marker}`;
    const next = replaceRange(text, sel.start, sel.end, wrapped);
    if (sel.start === sel.end) {
      // Empty selection: place the cursor between the markers.
      const caret = sel.start + marker.length;
      return { text: next, selection: { start: caret, end: caret } };
    }
    return {
      text: next,
      selection: { start: sel.start + marker.length, end: sel.end + marker.length },
    };
  };
}

// Find the [lineStart, lineEnd) offsets of every line the selection touches.
function lineRange(text: string, sel: Sel): { start: number; end: number } {
  const start = text.lastIndexOf("\n", sel.start - 1) + 1;
  let end = text.indexOf("\n", sel.end);
  if (end === -1) end = text.length;
  return { start, end };
}

// Apply a per-line prefix mutation across the selected lines.
function mapLines(mutate: (line: string, index: number) => string): Transform {
  return (text, sel) => {
    const { start, end } = lineRange(text, sel);
    const block = text.slice(start, end);
    const next = block.split("\n").map(mutate).join("\n");
    const replaced = replaceRange(text, start, end, next);
    return { text: replaced, selection: { start, end: start + next.length } };
  };
}

export const toggleBold = toggleWrap("**");
export const toggleItalic = toggleWrap("*");
export const toggleStrikethrough = toggleWrap("~~");
export const toggleInlineCode = toggleWrap("`");

export function setHeading(level: 1 | 2 | 3): Transform {
  const hashes = "#".repeat(level);
  return mapLines((line) => `${hashes} ${line.replace(/^#{1,6}\s+/, "")}`);
}

export const toggleBulletList: Transform = mapLines((line) =>
  line.startsWith("- ") ? line.slice(2) : `- ${line}`,
);

export const toggleNumberedList: Transform = mapLines((line, i) =>
  /^\d+\.\s/.test(line) ? line.replace(/^\d+\.\s/, "") : `${i + 1}. ${line}`,
);

export const toggleChecklist: Transform = mapLines((line) =>
  line.startsWith("- [ ] ") ? line.slice(6) : `- [ ] ${line}`,
);

export const toggleQuote: Transform = mapLines((line) =>
  line.startsWith("> ") ? line.slice(2) : `> ${line}`,
);

export function insertCodeBlock(lang = ""): Transform {
  return (text, sel) => {
    const selected = text.slice(sel.start, sel.end);
    const block = "```" + lang + "\n" + (selected || "") + "\n```";
    const next = replaceRange(text, sel.start, sel.end, block);
    const caret = sel.start + 3 + lang.length + 1; // start of code line
    return { text: next, selection: { start: caret, end: caret + selected.length } };
  };
}

export function insertTable(rows: number, cols: number): Transform {
  return (text, sel) => {
    const header = "| " + Array.from({ length: cols }, (_, c) => `Column ${c + 1}`).join(" | ") + " |";
    const divider = "| " + Array.from({ length: cols }, () => "---").join(" | ") + " |";
    const bodyRow = "| " + Array.from({ length: cols }, () => "   ").join(" | ") + " |";
    const body = Array.from({ length: rows }, () => bodyRow).join("\n");
    const table = [header, divider, body].join("\n");
    const next = replaceRange(text, sel.start, sel.end, table);
    return { text: next, selection: { start: sel.start, end: sel.start + table.length } };
  };
}

export function insertLink(label: string, href: string): Transform {
  return (text, sel) => {
    const text2 = label || text.slice(sel.start, sel.end) || "link";
    const md = `[${text2}](${href})`;
    const next = replaceRange(text, sel.start, sel.end, md);
    return { text: next, selection: { start: sel.start, end: sel.start + md.length } };
  };
}

export function insertImage(alt: string, src: string): Transform {
  return (text, sel) => {
    const md = `![${alt || "image"}](${src})`;
    const next = replaceRange(text, sel.start, sel.end, md);
    return { text: next, selection: { start: sel.start, end: sel.start + md.length } };
  };
}

export function insertHtmlBlock(): Transform {
  const scaffold = "<details>\n<summary>Details</summary>\n\nContent here.\n\n</details>";
  return (text, sel) => {
    const next = replaceRange(text, sel.start, sel.end, scaffold);
    return { text: next, selection: { start: sel.start, end: sel.start + scaffold.length } };
  };
}
