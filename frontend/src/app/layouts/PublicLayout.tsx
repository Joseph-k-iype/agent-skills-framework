import { Layout, Typography } from "antd";
import { useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { CommandPalette } from "@/shared/components/CommandPalette";

const { Header, Content } = Layout;

/** Public (logged-out) shell: top nav + ⌘K command palette, wraps the marketplace pages. */
export function PublicLayout() {
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <Layout style={{ minHeight: "100vh", background: tokens.color.canvas }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: tokens.space * 3,
          padding: "0 32px",
          background: tokens.color.surface,
          borderBottom: `1px solid ${tokens.color.line}`,
          height: 64,
          lineHeight: "64px",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: tokens.space * 3, minWidth: 0 }}>
          <Link
            to="/"
            style={{ display: "flex", alignItems: "center", gap: tokens.space, textDecoration: "none" }}
          >
            <span
              aria-hidden
              style={{
                width: 10,
                height: 10,
                background: tokens.color.accent,
                borderRadius: 2,
                flexShrink: 0,
              }}
            />
            <Typography.Text
              style={{
                color: tokens.color.ink,
                letterSpacing: "0.2em",
                fontSize: 13,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
              }}
            >
              Data Skill Marketplace
            </Typography.Text>
          </Link>

          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: tokens.space * 2,
              width: 320,
              height: 36,
              padding: "0 6px 0 14px",
              background: tokens.color.canvas,
              border: `1px solid ${tokens.color.line}`,
              borderRadius: tokens.radius,
              color: tokens.color.ink3,
              fontSize: 13,
              fontFamily: tokens.font.sans,
              cursor: "pointer",
            }}
          >
            <span>Search skills…</span>
            <span
              style={{
                padding: "2px 6px",
                background: tokens.color.surface,
                border: `1px solid ${tokens.color.lineStrong}`,
                borderRadius: 4,
                fontSize: 11,
                color: tokens.color.ink2,
                fontFamily: tokens.font.mono,
              }}
            >
              ⌘K
            </span>
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: tokens.space * 3, flexShrink: 0 }}>
          <Link to="/marketplace" style={{ color: tokens.color.ink2, fontSize: 14 }}>
            Browse
          </Link>
          <Link to="/docs" style={{ color: tokens.color.ink2, fontSize: 14 }}>
            Docs
          </Link>
          <Link
            to="/login"
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: 32,
              padding: "0 15px",
              background: tokens.color.ink,
              color: tokens.color.surface,
              border: "none",
              borderRadius: tokens.radius,
              fontSize: 14,
              textDecoration: "none",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = tokens.color.ink;
              e.currentTarget.style.color = tokens.color.surface;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = tokens.color.ink;
              e.currentTarget.style.color = tokens.color.surface;
            }}
          >
            Sign in
          </Link>
        </div>
      </Header>

      <Content>
        <div style={{ maxWidth: tokens.maxContentWidth, width: "100%", margin: "0 auto", padding: 28 }}>
          <Outlet />
        </div>
      </Content>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </Layout>
  );
}
