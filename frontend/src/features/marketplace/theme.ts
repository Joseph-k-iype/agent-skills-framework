import {
  ApartmentOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  MessageOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { ComponentType } from "react";

/** Per-type accent colors — the multi-color vibrancy that makes the storefront. */
export const TYPE_ACCENT: Record<string, string> = {
  skill: "#E82127", // Tesla Red (brand anchor)
  agent: "#2563EB",
  prompt: "#7C3AED",
  document: "#0F766E",
  workflow: "#B45309",
};

const TYPE_ICON: Record<string, ComponentType> = {
  skill: ThunderboltOutlined,
  agent: RobotOutlined,
  prompt: MessageOutlined,
  document: FileTextOutlined,
  workflow: ApartmentOutlined,
};

export function accentFor(type?: string | null): string {
  return TYPE_ACCENT[(type ?? "").toLowerCase()] ?? "#5B5B61";
}

/** Per-category accent colors — muted, desaturated wayfinding hues. Tesla
 * Red is reserved exclusively for the featured tick, so none of these may
 * be red or near `tokens.color.accent` (#E82127). */
export const CATEGORY_ACCENT: Record<string, string> = {
  transformation: "#3B5BA9",
  enrichment: "#2E7D6B",
  validation: "#4B7A3F",
  extraction: "#B07A2E",
  prompt: "#6B4FA0",
  toolkit: "#4A4A52",
};

export function categoryAccentFor(category?: string | null): string {
  return CATEGORY_ACCENT[(category ?? "").toLowerCase()] ?? "#8A8A90";
}

export function iconFor(type?: string | null): ComponentType {
  return TYPE_ICON[(type ?? "").toLowerCase()] ?? AppstoreOutlined;
}

/** A soft tinted background derived from an accent (for icon chips / spines). */
export function tint(hex: string, alpha = 0.12): string {
  const n = hex.replace("#", "");
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
