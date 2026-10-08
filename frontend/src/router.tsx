/* Code-based TanStack Router tree. Pages are lazy so the study screens stay small. */

import type { QueryClient } from "@tanstack/react-query";
import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  lazyRouteComponent,
  redirect,
} from "@tanstack/react-router";

import { AppShell } from "@/components/layout/AppShell";
import { RootLayout } from "@/components/layout/RootLayout";
import { isApiError } from "@/lib/api";
import { meQueryOptions } from "@/queries/auth";

export interface RouterContext {
  queryClient: QueryClient;
}

const rootRoute = createRootRouteWithContext<RouterContext>()({ component: RootLayout });

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: lazyRouteComponent(() => import("@/pages/LoginPage")),
});

const shellRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "shell",
  component: AppShell,
  beforeLoad: async ({ context, location }) => {
    try {
      const me = await context.queryClient.ensureQueryData(meQueryOptions());
      if (me.onboarding_required && location.pathname !== "/onboarding") {
        throw redirect({ to: "/onboarding" });
      }
      return { me };
    } catch (error) {
      if (isApiError(error, 401)) throw redirect({ to: "/login" });
      throw error;
    }
  },
});

// Generic over the path so each literal survives into the typed route tree.
const page = <TPath extends string>(
  path: TPath,
  loader: () => Promise<{ default: React.ComponentType }>,
) => createRoute({ getParentRoute: () => shellRoute, path, component: lazyRouteComponent(loader) });

const reviewRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/review",
  component: lazyRouteComponent(() => import("@/pages/ReviewPage")),
  validateSearch: (search: Record<string, unknown>): { limit?: number } => {
    const limit = Number(search["limit"]);
    return Number.isFinite(limit) && limit > 0 ? { limit } : {};
  },
});

const playerRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/watch/$course/play",
  component: lazyRouteComponent(() => import("@/pages/PlayerPage")),
  validateSearch: (search: Record<string, unknown>): { lecture: string } => ({
    lecture: typeof search["lecture"] === "string" ? search["lecture"] : "",
  }),
});

const routes = [
  page("/", () => import("@/pages/TodayPage")),
  page("/watch", () => import("@/pages/WatchPage")),
  page("/watch/$course", () => import("@/pages/CoursePage")),
  playerRoute,
  page("/onboarding", () => import("@/pages/OnboardingPage")),
  page("/learn", () => import("@/pages/LearnPage")),
  page("/learn/$key", () => import("@/pages/LessonPage")),
  page("/practice", () => import("@/pages/PracticePage")),
  page("/practice/$sessionId", () => import("@/pages/SessionPage")),
  reviewRoute,
  page("/review/cards", () => import("@/pages/CardsPage")),
  page("/progress", () => import("@/pages/ProgressPage")),
  page("/labs", () => import("@/pages/LabsPage")),
  page("/labs/$key", () => import("@/pages/LabPage")),
  page("/settings", () => import("@/pages/SettingsPage")),
  page("/content", () => import("@/pages/ContentPage")),
  page("/content/$key", () => import("@/pages/ContentItemPage")),
];

const routeTree = rootRoute.addChildren([loginRoute, shellRoute.addChildren(routes)]);

export function createAppRouter(queryClient: QueryClient) {
  return createRouter({
    routeTree,
    context: { queryClient },
    defaultPreload: "intent",
    scrollRestoration: true,
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
