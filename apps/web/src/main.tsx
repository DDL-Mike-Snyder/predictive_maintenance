import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { routes } from "./routes";
import { queryClient } from "./api/queryClient";
import "./styles/tokens.css";
import "./styles/global.css";

// 51-operator-console.md §2: `createBrowserRouter(routes, { basename:
// import.meta.env.BASE_URL })`.
const router = createBrowserRouter(routes, { basename: import.meta.env.BASE_URL });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
