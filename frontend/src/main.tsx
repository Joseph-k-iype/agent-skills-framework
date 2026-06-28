import { ConfigProvider, App as AntApp } from "antd";
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { antdTheme } from "./app/theme/antdTheme";
import { QueryProvider } from "./app/providers/QueryProvider";
import { AuthProvider } from "./app/providers/AuthProvider";
import { router } from "./router";
import "@xyflow/react/dist/style.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider theme={antdTheme}>
      <AntApp>
        <QueryProvider>
          <AuthProvider>
            <RouterProvider router={router} />
          </AuthProvider>
        </QueryProvider>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
