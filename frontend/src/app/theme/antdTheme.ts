import type { ThemeConfig } from "antd";
import { tokens } from "./tokens";

/**
 * Ant Design theme tuned toward a restrained, Swiss/Apple-like feel:
 * flat surfaces, hairline borders, generous whitespace, one accent colour.
 */
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: tokens.color.accent,
    colorInfo: tokens.color.accent,
    colorSuccess: tokens.color.ok,
    colorWarning: tokens.color.warn,
    colorError: tokens.color.bad,

    colorText: tokens.color.ink,
    colorTextSecondary: tokens.color.ink2,
    colorTextTertiary: tokens.color.ink3,
    colorBgLayout: tokens.color.canvas,
    colorBgContainer: tokens.color.surface,
    colorBorder: tokens.color.line,
    colorBorderSecondary: tokens.color.line,

    borderRadius: tokens.radius,
    fontFamily: tokens.font.sans,
    fontSize: 14,
    controlHeight: 36,
    wireframe: false,
    boxShadow: "0 1px 2px rgba(17,17,20,0.04), 0 8px 24px rgba(17,17,20,0.04)",
  },
  components: {
    Layout: {
      headerBg: tokens.color.surface,
      headerHeight: 56,
      siderBg: tokens.color.surface,
      bodyBg: tokens.color.canvas,
    },
    Menu: {
      itemBg: "transparent",
      itemSelectedBg: "#FCEDED",
      itemSelectedColor: tokens.color.accent,
      itemHeight: 38,
    },
    Button: {
      primaryShadow: "none",
      defaultShadow: "none",
      fontWeight: 500,
    },
    Card: {
      paddingLG: 24,
    },
    Table: {
      headerBg: tokens.color.canvas,
      headerColor: tokens.color.ink2,
      borderColor: tokens.color.line,
    },
  },
};
