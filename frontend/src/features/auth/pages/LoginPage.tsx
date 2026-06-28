import { App as AntApp, Button, Form, Input, Typography } from "antd";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { ApiError } from "@/shared/api/client";
import { useAuthStore } from "@/stores/authStore";
import { login } from "../api/authApi";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { message } = AntApp.useApp();
  const setSession = useAuthStore((s) => s.setSession);
  const [loading, setLoading] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  async function onFinish(values: { username: string; password: string }) {
    setLoading(true);
    try {
      const res = await login(values.username, values.password);
      setSession(res.tokens.access_token, res.tokens.refresh_token, res.user);
      navigate(from, { replace: true });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Login failed";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        background: tokens.color.canvas,
      }}
    >
      {/* Left: editorial brand panel */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px 56px",
          borderRight: `1px solid ${tokens.color.line}`,
          background: tokens.color.surface,
        }}
      >
        <div style={{ fontSize: 13, letterSpacing: "0.22em", color: tokens.color.ink3 }}>
          EAKSO
        </div>
        <div>
          <Typography.Title level={1} style={{ margin: 0, fontSize: 44, lineHeight: 1.08 }}>
            Enterprise knowledge,
            <br />
            engineered into skills.
          </Typography.Title>
          <Typography.Paragraph
            style={{ marginTop: 20, maxWidth: 460, color: tokens.color.ink2, fontSize: 16 }}
          >
            Author, organize, evaluate and share AI agent skills on a knowledge-graph-native
            operating system.
          </Typography.Paragraph>
        </div>
        <div style={{ height: 3, width: 56, background: tokens.color.accent }} />
      </div>

      {/* Right: sign-in */}
      <div style={{ display: "grid", placeItems: "center", padding: 24 }}>
        <div style={{ width: 360, maxWidth: "100%" }}>
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            Sign in
          </Typography.Title>
          <Typography.Text type="secondary">Use your enterprise directory account.</Typography.Text>
          <Form layout="vertical" onFinish={onFinish} requiredMark={false} style={{ marginTop: 28 }}>
            <Form.Item
              label="Username"
              name="username"
              rules={[{ required: true, message: "Enter your username" }]}
            >
              <Input size="large" autoFocus placeholder="admin" autoComplete="username" />
            </Form.Item>
            <Form.Item
              label="Password"
              name="password"
              rules={[{ required: true, message: "Enter your password" }]}
            >
              <Input.Password size="large" placeholder="••••••••" autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" size="large" block loading={loading}>
              Continue
            </Button>
          </Form>
        </div>
      </div>
    </div>
  );
}
