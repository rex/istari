import { useQuery } from "@tanstack/react-query";

import { formatDateTime } from "@/lib/format";
import { healthQueryOptions } from "@/queries/health";

// The badge also renders on the login page, before any settings exist, so it uses the
// browser's zone rather than the owner's configured one.
const ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;
const known = (commit: string) => commit !== "unknown";

/** Version · commit · build time · process start, on every page. The API is the source of truth. */
export function BuildBadge() {
  const health = useQuery(healthQueryOptions());
  const api = health.data;
  const version = api?.version ?? __WEB_VERSION__;
  const commit = api?.commit ?? __WEB_COMMIT__;
  const stale =
    api !== undefined &&
    known(api.commit) &&
    known(__WEB_COMMIT__) &&
    api.commit !== __WEB_COMMIT__;

  // Real separators in the text, so the badge reads the same to a screen reader, a test
  // and a copy-paste as it does on screen.
  const parts = [`Istari v${version}`, commit];
  if (api?.built_at) parts.push(`built ${formatDateTime(api.built_at, ZONE)}`);
  if (api) parts.push(`up since ${formatDateTime(api.started_at, ZONE)}`);

  return (
    <p className="build-badge" aria-label="Build information">
      <span>{parts.join(" · ")}</span>
      {health.isError ? <span className="build-badge__warn"> · API unreachable</span> : null}
      {stale ? (
        <span className="build-badge__warn" role="status">
          {" · "}this page is build {__WEB_COMMIT__}; the API is newer, reload
        </span>
      ) : null}
    </p>
  );
}
