// frontend/src/features/concepts/components/editor/EditorToolbar.tsx
import {
  BoldOutlined,
  ItalicOutlined,
  StrikethroughOutlined,
  CodeOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  CheckSquareOutlined,
  LinkOutlined,
  TableOutlined,
  PictureOutlined,
  Html5Outlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import { Button, Dropdown, Space, Tooltip } from "antd";
import { tokens } from "@/app/theme/tokens";
import {
  insertCodeBlock,
  insertHtmlBlock,
  insertImage,
  insertTable,
  setHeading,
  toggleBold,
  toggleBulletList,
  toggleChecklist,
  toggleInlineCode,
  toggleItalic,
  toggleNumberedList,
  toggleQuote,
  toggleStrikethrough,
  type Transform,
} from "@/features/concepts/lib/markdownTransforms";
import { MERMAID_KINDS, insertMermaid } from "@/features/concepts/lib/mermaidTemplates";

export function EditorToolbar({
  onApply,
  onInsertConceptLink,
}: {
  onApply: (t: Transform) => void;
  onInsertConceptLink: () => void;
}) {
  const btn = (label: string, icon: React.ReactNode, t: Transform) => (
    <Tooltip title={label} key={label}>
      <Button size="small" type="text" aria-label={label} icon={icon} onClick={() => onApply(t)} />
    </Tooltip>
  );

  const headingItems = [1, 2, 3].map((lvl) => ({
    key: `h${lvl}`,
    label: `Heading ${lvl}`,
    onClick: () => onApply(setHeading(lvl as 1 | 2 | 3)),
  }));

  const mermaidItems = MERMAID_KINDS.map((k) => ({
    key: k,
    label: `Mermaid: ${k}`,
    onClick: () => onApply(insertMermaid(k)),
  }));

  return (
    <Space
      wrap
      size={2}
      style={{
        padding: "6px 8px",
        borderBottom: `1px solid ${tokens.color.line}`,
        background: tokens.color.surface,
      }}
    >
      {btn("Bold", <BoldOutlined />, toggleBold)}
      {btn("Italic", <ItalicOutlined />, toggleItalic)}
      {btn("Strikethrough", <StrikethroughOutlined />, toggleStrikethrough)}
      {btn("Inline code", <CodeOutlined />, toggleInlineCode)}
      <Dropdown menu={{ items: headingItems }} trigger={["click"]}>
        <Button size="small" type="text" aria-label="Heading">H</Button>
      </Dropdown>
      {btn("Bullet list", <UnorderedListOutlined />, toggleBulletList)}
      {btn("Numbered list", <OrderedListOutlined />, toggleNumberedList)}
      {btn("Checklist", <CheckSquareOutlined />, toggleChecklist)}
      {btn("Quote", <span style={{ fontFamily: tokens.font.mono }}>&gt;</span>, toggleQuote)}
      {btn("Code block", <CodeOutlined />, insertCodeBlock(""))}
      {btn("Table", <TableOutlined />, insertTable(3, 3))}
      <Dropdown menu={{ items: mermaidItems }} trigger={["click"]}>
        <Tooltip title="Mermaid diagram">
          <Button size="small" type="text" aria-label="Mermaid" icon={<NodeIndexOutlined />} />
        </Tooltip>
      </Dropdown>
      {btn("Image", <PictureOutlined />, insertImage("image", "https://"))}
      {btn("HTML block", <Html5Outlined />, insertHtmlBlock())}
      <Tooltip title="Link a concept (graph edge)">
        <Button
          size="small"
          type="text"
          aria-label="Link concept"
          icon={<LinkOutlined />}
          onClick={onInsertConceptLink}
        />
      </Tooltip>
    </Space>
  );
}

export default EditorToolbar;
