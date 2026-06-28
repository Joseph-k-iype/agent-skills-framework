import {
  AppstoreOutlined,
  AuditOutlined,
  DashboardOutlined,
  DeploymentUnitOutlined,
  FolderOpenOutlined,
  SafetyOutlined,
  ShopOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import type { ComponentType } from "react";
import type { Role } from "@/stores/authStore";

export interface NavItem {
  key: string;
  label: string;
  icon: ComponentType;
  group?: string;
}

// Developer + Admin sidebar (Phase 0–3 surface; later phases append items).
const DEVELOPER_NAV: NavItem[] = [
  { key: "/dashboard", label: "Dashboard", icon: DashboardOutlined },
  { key: "/workspace", label: "Workspace", icon: FolderOpenOutlined },
  { key: "/knowledge", label: "Knowledge Graph", icon: DeploymentUnitOutlined },
  { key: "/skills", label: "Skills", icon: AppstoreOutlined },
];

const ADMIN_NAV: NavItem[] = [
  { key: "/admin/users", label: "Users", icon: TeamOutlined, group: "Administration" },
  { key: "/admin/roles", label: "Roles", icon: SafetyOutlined, group: "Administration" },
  { key: "/admin/audit", label: "Audit Log", icon: AuditOutlined, group: "Administration" },
];

// Consumer top nav (marketplace experience).
const CONSUMER_NAV: NavItem[] = [
  { key: "/marketplace", label: "Marketplace", icon: ShopOutlined },
];

export function navForRole(role: Role): NavItem[] {
  if (role === "consumer") return CONSUMER_NAV;
  if (role === "admin") return [...DEVELOPER_NAV, ...ADMIN_NAV];
  return DEVELOPER_NAV;
}
