import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import React from "react";
import ReactDOM from "react-dom/client";
import { ErrorBoundary } from "react-error-boundary";

import { ApiError, setUnauthenticatedHandler } from "@/lib/api";
import { createAppRouter } from "@/router";

import "./styles/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false;
        return failureCount < 1;
      },
    },
    mutations: { retry: 0 },
  },
});

const router = createAppRouter(queryClient);

setUnauthenticatedHandler(() => {
  queryClient.removeQueries({ queryKey: ["auth"] });
  if (router.state.location.pathname !== "/login") {
    void router.navigate({ to: "/login" });
  }
});

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <ErrorBoundary
      fallbackRender={({ error }) => (
        <main style={{ padding: "2rem", maxWidth: "60ch" }}>
          <h1>Something broke</h1>
          <p>{error instanceof Error ? error.message : "Unknown error"}</p>
          <a href="/">Back to Today</a>
        </main>
      )}
    >
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
