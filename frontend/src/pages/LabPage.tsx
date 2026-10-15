import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";

import { LabEvidence } from "@/components/feature/LabEvidence";
import { VerifiedLab } from "@/components/feature/VerifiedLab";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { Markdown } from "@/lib/Markdown";
import type { LabView } from "@/lib/types";
import { meQueryOptions } from "@/queries/auth";
import { labQueryOptions } from "@/queries/labs";

function Sources({ lab }: { lab: LabView }) {
  return (
    <ul className="sources">
      {lab.sources.map((s) => (
        <li key={s.url}>
          <a href={s.url} target="_blank" rel="noopener noreferrer">
            {s.title}
          </a>{" "}
          <span className="muted">(checked {s.checked_on})</span>
        </li>
      ))}
    </ul>
  );
}

function Eyebrow({ lab }: { lab: LabView }) {
  return (
    <p className="card__eyebrow">
      <Link to="/labs">Labs</Link> · {lab.objectives.map((o) => o.code).join(" · ")} · ~
      {lab.estimated_minutes} min
    </p>
  );
}

/** A brief followed by hand in the owner's own account: the long form, every section shown. */
function ManualLab({ lab }: { lab: LabView }) {
  return (
    <article className="reader">
      <Eyebrow lab={lab} />
      <h1>{lab.title}</h1>
      <div className="cost-warning">
        <strong>Cost warning.</strong> <Markdown inline>{lab.cost_warning_md}</Markdown>
      </div>
      <h2>Goals</h2>
      <Markdown>{lab.goals_md}</Markdown>
      <h2>Prerequisites</h2>
      <Markdown>{lab.prerequisites_md}</Markdown>
      <h2>Steps (manual)</h2>
      <Markdown>{lab.steps_md}</Markdown>
      <h2>Expected observations</h2>
      <Markdown>{lab.expected_observations_md}</Markdown>
      <h2>Cleanup</h2>
      <Markdown>{lab.cleanup_md}</Markdown>
      <h2>Sources</h2>
      <Sources lab={lab} />
    </article>
  );
}

/** A lab the cluster grades: the loop up front, the brief's own notes folded underneath. */
function GradedLab({ lab, timeZone }: { lab: LabView; timeZone: string }) {
  const verifier = lab.verifier;
  return (
    <article className="stack">
      <header className="lab-head">
        <Eyebrow lab={lab} />
        <h1>{lab.title}</h1>
        <div className="lab-head__meta">
          <Badge tone="gold">Verified on the lab cluster</Badge>
          {verifier ? (
            <span>
              {verifier.profile} · {verifier.question} · weight {verifier.weight}
              {verifier.time_limit_minutes ? ` · ${verifier.time_limit_minutes} min limit` : ""}
            </span>
          ) : null}
        </div>
      </header>
      <VerifiedLab lab={lab} timeZone={timeZone} />
      <details className="disclosure">
        <summary>About this lab: goals, prerequisites, what to expect, cleanup, sources</summary>
        <div className="prose">
          <h3>Goals</h3>
          <Markdown>{lab.goals_md}</Markdown>
          <h3>Prerequisites</h3>
          <Markdown>{lab.prerequisites_md}</Markdown>
          <h3>Expected observations</h3>
          <Markdown>{lab.expected_observations_md}</Markdown>
          <h3>Cleanup</h3>
          <Markdown>{lab.cleanup_md}</Markdown>
          <p className="muted small">
            <Markdown inline>{lab.cost_warning_md}</Markdown>
          </p>
          <h3>Sources</h3>
          <Sources lab={lab} />
        </div>
      </details>
    </article>
  );
}

export default function LabPage() {
  const { key = "" } = useParams({ strict: false });
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const lab = useQuery(labQueryOptions(key));
  if (lab.isPending) return <Spinner label="Opening lab" />;
  if (lab.isError)
    return <StateBlock tone="error" title="Could not open this lab" body={lab.error.message} />;
  const data = lab.data;
  const timeZone = me.settings.timezone;

  return (
    <div className="with-rail">
      {data.verifier ? <GradedLab lab={data} timeZone={timeZone} /> : <ManualLab lab={data} />}
      <aside className="with-rail__rail">
        <LabEvidence labKey={key} evidence={data.evidence} timeZone={timeZone} />
      </aside>
    </div>
  );
}
