import { Layout, Menu, Typography } from "antd";
import { createElement, useMemo } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { useAuthStore } from "@/stores/authStore";
import { navForRole } from "./nav";
import { UserMenu } from "./UserMenu";

const { Header, Sider, Content } = Layout;

/** Developer & Admin shell: slim left sidebar + header. */
export function SidebarLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const role = useAuthStore((s) => s.user?.role ?? "developer");

  const items = useMemo(() => {
    const nav = navForRole(role);
    const groups = new Map<string | undefined, typeof nav>();
    nav.forEach((n) => {
      const g = groups.get(n.group) ?? [];
      g.push(n);
      groups.set(n.group, g);
    });
    const out: NonNullable<Parameters<typeof Menu>[0]["items"]> = [];
    for (const [group, list] of groups) {
      if (group) out.push({ type: "divider" });
      list.forEach((n) =>
        out.push({ key: n.key, icon: createElement(n.icon), label: n.label }),
      );
    }
    return out;
  }, [role]);

  const selected = "/" + (location.pathname.split("/")[1] || "dashboard");

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={232}
        theme="light"
        style={{ borderRight: `1px solid ${tokens.color.line}`, position: "sticky", top: 0, height: "100vh" }}
      >
        <div style={{ padding: "20px 24px 12px", letterSpacing: "0.2em", fontSize: 13, color: tokens.color.ink }}>
          EAKSO
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          items={items}
          style={{ borderInlineEnd: "none", padding: "0 8px" }}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            padding: "0 28px",
            borderBottom: `1px solid ${tokens.color.line}`,
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <UserMenu />
        </Header>
        <Content style={{ padding: 28, maxWidth: tokens.maxContentWidth, width: "100%", margin: "0 auto" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

/** Consumer shell: top nav, no sidebar (marketplace experience). */
export function TopNavLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          borderBottom: `1px solid ${tokens.color.line}`,
        }}
      >
        <Typography.Text style={{ letterSpacing: "0.2em", fontSize: 13 }}>EAKSO</Typography.Text>
        <UserMenu />
      </Header>
      <Content style={{ padding: 28, maxWidth: tokens.maxContentWidth, width: "100%", margin: "0 auto" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
