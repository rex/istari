import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BuildBadge } from "@/components/layout/BuildBadge";
import { api } from "@/lib/api";
import type { HealthView } from "@/lib/types";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));

const healthy: HealthView = {
  status: "ok",
  reason: null,
  version: "1.2.3",
  commit: __WEB_COMMIT__,
  built_at: "2026-10-07T00:00:00+00:00",
  started_at: "2026-10-07T01:30:00+00:00",
};

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("<BuildBadge />", () => {
  beforeEach(() => {
    vi.mocked(api).mockReset();
  });

  it("shows the API's version, commit, build time and start time with real separators", async () => {
    vi.mocked(api).mockResolvedValue(healthy);
    renderWithClient(<BuildBadge />);
    const badge = screen.getByLabelText("Build information");
    await expect
      .poll(() => badge.textContent)
      .toMatch(/Istari v1\.2\.3 · \S+ · built .* · up since /);
    expect(badge).toHaveTextContent(__WEB_COMMIT__);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("warns when the loaded bundle is a different build than the API", async () => {
    vi.mocked(api).mockResolvedValue({ ...healthy, commit: "0000000" });
    renderWithClient(<BuildBadge />);
    const warning = await screen.findByRole("status");
    expect(warning).toHaveTextContent(/the API is newer, reload/);
  });

  it("falls back to the bundle's own stamp when the API is down", async () => {
    vi.mocked(api).mockRejectedValue(new Error("down"));
    renderWithClient(<BuildBadge />);
    expect(await screen.findByText(/API unreachable/)).toBeInTheDocument();
    expect(screen.getByLabelText("Build information")).toHaveTextContent(
      `Istari v${__WEB_VERSION__}`,
    );
  });
});
