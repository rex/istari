import { Link, Outlet } from "@tanstack/react-router";
import { Suspense, useState } from "react";
import { ErrorBoundary } from "react-error-boundary";

import { GlobalShortcuts } from "@/components/feature/GlobalShortcuts";
import { ShortcutsHelp } from "@/components/feature/ShortcutsHelp";
import { Brand } from "@/components/layout/Brand";
import { BuildBadge } from "@/components/layout/BuildBadge";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { useUIStore } from "@/stores/ui";

// Under 720px the stylesheet turns this nav into a bottom tab bar of five; a `desk` item is
// dropped from the bar (Progress is occasional and table-heavy) and listed under More.
const NAV = [
  { to: "/", label: "Today", exact: true, desk: false },
  { to: "/learn", label: "Learn", exact: false, desk: false },
  { to: "/practice", label: "Practice", exact: false, desk: false },
  { to: "/review", label: "Review", exact: false, desk: false },
  { to: "/progress", label: "Progress", exact: false, desk: true },
  { to: "/watch", label: "Watch", exact: false, desk: false },
] as const;

export function AppShell() {
  const focusMode = useUIStore((s) => s.focusMode);
  const setFocusMode = useUIStore((s) => s.setFocusMode);
  const [moreOpen, setMoreOpen] = useState(false);

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
            {NAV.map((item) => {
              const base = item.desk ? "nav__link nav__link--desk" : "nav__link";
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={base}
                  activeOptions={{ exact: item.exact }}
                  activeProps={{ className: `${base} nav__link--active`, "aria-current": "page" }}
                >
                  {item.label}
                </Link>
              );
            })}
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
          <button
            type="button"
            className="btn btn--ghost btn--sm topbar__more"
            aria-haspopup="dialog"
            aria-expanded={moreOpen}
            onClick={() => setMoreOpen(true)}
          >
            More
          </button>
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
      <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
      <GlobalShortcuts />
    </div>
  );
}
