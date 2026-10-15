import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatRelative, pluralize } from "@/lib/format";
import type { DomainView, LabSummary } from "@/lib/types";
import { healthQueryOptions } from "@/queries/health";
import { labsQueryOptions } from "@/queries/labs";
import { trackQueryOptions } from "@/queries/track";

/** Where a lab stands, in one glance: the latest verdict for graded labs, notes for manual ones. */
function LabStatus({ lab }: { lab: LabSummary }) {
  if (lab.verifier) {
    const last = lab.last_attempt;
    if (last) {
      return (
        <span className="lab-card__status">
          <Badge tone={last.passed ? "success" : "danger"}>
            {last.passed ? "passed" : "failed"} · {formatRelative(last.checked_at)}
          </Badge>
          {!last.passed && last.reason_line ? (
            <span className="lab-card__reason" title={last.reason_line}>
              {last.reason_line}
            </span>
          ) : null}
        </span>
      );
    }
    return <Badge>{lab.attempt_count > 0 ? "set up, not checked" : "not started"}</Badge>;
  }
  return lab.evidence_count > 0 ? (
    <Badge tone="success">{pluralize(lab.evidence_count, "evidence note")}</Badge>
  ) : (
    <Badge>not started</Badge>
  );
}

function LabRow({ lab }: { lab: LabSummary }) {
  const meta = [
    `~${lab.estimated_minutes} min`,
    lab.objectives.map((o) => o.code).join(", "),
    lab.verifier ? `${lab.verifier.profile} · weight ${lab.verifier.weight}` : null,
  ].filter(Boolean);
  return (
    <Link
      to="/labs/$key"
      params={{ key: lab.item_key }}
      className="card card--quiet lesson-row"
      data-lab={lab.item_key}
    >
      <span>
        <span className="lesson-row__title">{lab.title}</span>
        <span className="lesson-row__meta">{meta.join(" · ")}</span>
      </span>
      <LabStatus lab={lab} />
    </Link>
  );
}

/** The lab cluster's state from the API's last background poll; never a live call from here. */
function ClusterStrip() {
  const health = useQuery(healthQueryOptions());
  const k16s = health.data?.k16s;
  if (!k16s) return null;
  const tone = !k16s.configured
    ? "neutral"
    : k16s.reachable === null
      ? "neutral"
      : k16s.reachable
        ? "success"
        : "danger";
  const text = !k16s.configured
    ? "No lab cluster configured. Set K16S_BASE_URL to grade labs on your own K16S instance."
    : k16s.reachable === null
      ? "Checking the lab cluster…"
      : k16s.reachable
        ? `Lab cluster ready · ${k16s.mode ?? "mode unknown"} · profiles ${k16s.profiles.join(", ") || "none"}`
        : `Lab cluster unreachable${k16s.checked_at ? ` · last checked ${formatRelative(k16s.checked_at)}` : ""}`;
  return (
    <div className="lab-strip" role="status">
      <span className={`lab-chip__dot lab-chip__dot--${tone}`} aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

/** Labs whose latest verdict is a pass. Progress keeps the stricter first-attempt view. */
function passedCount(labs: LabSummary[]): number {
  return labs.filter((lab) => lab.last_attempt?.passed === true).length;
}

/** Verified labs under their first objective's domain, in the track's order; within a
 *  domain by objective code, then title, so the list reads like the curriculum. */
function groupByDomain(labs: LabSummary[], domains: DomainView[]) {
  const names = new Map(domains.map((d) => [d.code, `${d.code}. ${d.name}`]));
  const groups = new Map<string, LabSummary[]>();
  for (const lab of labs) {
    const code = lab.objectives[0]?.domain_code ?? "";
    groups.set(code, [...(groups.get(code) ?? []), lab]);
  }
  const order = (lab: LabSummary) => `${lab.objectives[0]?.code ?? ""} ${lab.title}`;
  const numeric = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });
  return [...groups.entries()]
    .sort(([a], [b]) => numeric(a, b))
    .map(([code, list]) => ({
      code,
      title: names.get(code) ?? (code ? `Domain ${code}` : "Other"),
      labs: [...list].sort((a, b) => numeric(order(a), order(b))),
    }));
}

export default function LabsPage() {
  const labs = useQuery(labsQueryOptions());
  const track = useQuery(trackQueryOptions());
  if (labs.isPending) return <Spinner label="Loading lab briefs" />;
  if (labs.isError)
    return <StateBlock tone="error" title="Could not load labs" body={labs.error.message} />;
  const verified = labs.data.filter((lab) => lab.verifier);
  const manual = labs.data.filter((lab) => !lab.verifier);
  return (
    <div className="stack">
      <div className="page-head">
        <h1>Labs</h1>
        <p>
          Hands-on practice. Verified labs run on your lab cluster and are graded by it; the rest
          are briefs you follow by hand in your own account. Istari never provisions anything and
          never assumes a lab is free.
        </p>
      </div>
      {verified.length > 0 ? (
        <section className="stack" aria-labelledby="verified-labs">
          <ClusterStrip />
          <div className="domain-head">
            <h2 id="verified-labs">Verified on the lab cluster</h2>
            <span className="muted small">
              {pluralize(verified.length, "lab")} · {passedCount(verified)} passed
            </span>
          </div>
          {groupByDomain(verified, track.data?.domains ?? []).map((group) => (
            <div key={group.code} className="lab-group">
              <div className="domain-head">
                <h3>{group.title}</h3>
                <span className="muted small">
                  {passedCount(group.labs)}/{group.labs.length} passed
                </span>
              </div>
              <div className="lesson-list">
                {group.labs.map((lab) => (
                  <LabRow key={lab.item_key} lab={lab} />
                ))}
              </div>
            </div>
          ))}
        </section>
      ) : null}
      {manual.length > 0 ? (
        <section className="stack" aria-labelledby="manual-labs">
          <div className="domain-head">
            <h2 id="manual-labs">By hand, in your own account</h2>
            <span className="muted small">{pluralize(manual.length, "brief")}</span>
          </div>
          <div className="lesson-list">
            {manual.map((lab) => (
              <LabRow key={lab.item_key} lab={lab} />
            ))}
          </div>
        </section>
      ) : null}
      {labs.data.length === 0 ? (
        <StateBlock
          title="No labs in this track yet"
          body="Import a content pack with labs (make seed) or check Settings → Content."
        />
      ) : null}
    </div>
  );
}
