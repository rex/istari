import { Link, Outlet } from "@tanstack/react-router";
import { Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import { GlobalShortcuts } from "@/components/feature/GlobalShortcuts";
import { ShortcutsHelp } from "@/components/feature/ShortcutsHelp";
import { Brand } from "@/components/layout/Brand";
import { BuildBadge } from "@/components/layout/BuildBadge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { useUIStore } from "@/stores/ui";

const NAV = [
  { to: "/", label: "Today", exact: true },
  { to: "/learn", label: "Learn" },
  { to: "/practice", label: "Practice" },
  { to: "/review", label: "Review" },
  { to: "/progress", label: "Progress" },
  { to: "/watch", label: "Watch" },
] as const;

export function AppShell() {
  const focusMode = useUIStore((s) => s.focusMode);
  const setFocusMode = useUIStore((s) => s.setFocusMode);

  return (
    <div className={`shell ${focusMode ? "shell--focus" : ""}`}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {focusMode ? (
        <div className="focus-bar">
          <Brand compact />
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setFocusMode(false)}
          >
            Exit focus mode
          </button>
        </div>
      ) : (
        <header className="topbar">
          <Link to="/" className="topbar__brand" aria-label="Istari, Today">
            <Brand />
          </Link>
          <nav className="nav" aria-label="Primary">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="nav__link"
                activeOptions={{ exact: "exact" in item && item.exact }}
                activeProps={{ className: "nav__link nav__link--active", "aria-current": "page" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <nav className="nav nav--secondary" aria-label="Secondary">
            <Link
              to="/labs"
              className="nav__link"
              activeProps={{ className: "nav__link nav__link--active" }}
            >
              Labs
            </Link>
            <Link
              to="/settings"
              className="nav__link"
              activeProps={{ className: "nav__link nav__link--active" }}
            >
              Settings
            </Link>
          </nav>
        </header>
      )}
      <main id="main" className="main">
        <ErrorBoundary
          fallbackRender={({ error }) => (
            <StateBlock
              tone="error"
              title="This screen hit an error"
              body={error instanceof Error ? error.message : "Unknown error"}
            />
          )}
        >
          <Suspense fallback={<Spinner label="Loading" />}>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
      <footer className="footer">
        <BuildBadge />
      </footer>
      <ShortcutsHelp />
      <GlobalShortcuts />
    </div>
  );
}
