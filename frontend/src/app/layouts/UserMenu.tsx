import { LogoutOutlined, UserOutlined } from "@ant-design/icons";
import { Avatar, Dropdown, Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { tokens } from "@/app/theme/tokens";
import { useAuthStore } from "@/stores/authStore";

const ROLE_LABEL: Record<string, string> = {
  consumer: "Consumer",
  developer: "Developer",
  admin: "Admin",
};

export function UserMenu() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  if (!user) return null;

  return (
    <Dropdown
      trigger={["click"]}
      menu={{
        items: [
          {
            key: "logout",
            icon: <LogoutOutlined />,
            label: "Sign out",
            onClick: () => {
              clear();
              navigate("/login", { replace: true });
            },
          },
        ],
      }}
    >
      <Space style={{ cursor: "pointer" }} size="small">
        <Avatar size={28} icon={<UserOutlined />} style={{ background: tokens.color.ink }} />
        <Typography.Text strong>{user.full_name ?? user.username}</Typography.Text>
        <Tag bordered={false} color="default">
          {ROLE_LABEL[user.role] ?? user.role}
        </Tag>
      </Space>
    </Dropdown>
  );
}
