import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { VerifiedLab } from "@/components/feature/VerifiedLab";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Markdown } from "@/lib/Markdown";
import type { LabSummary } from "@/lib/types";
import { labQueryOptions } from "@/queries/labs";

/** One lab inside the lesson. A graded lab shows its task and the three steps, as the lab
    page does; a brief shows what to do and what to expect. Evidence, cleanup and sources
    stay on the lab page. */
function DoItLab({ summary, timeZone }: { summary: LabSummary; timeZone: string }) {
  const lab = useQuery(labQueryOptions(summary.item_key));
  return (
    <article className="card stack" data-do-it={summary.item_key}>
      <div className="spread">
        <h3>{summary.title}</h3>
        <span className="cluster small muted">
          {summary.verifier ? (
            <Badge tone="gold">graded on the lab cluster</Badge>
          ) : (
            <Badge>by hand, in your own account</Badge>
          )}
          <span>~{summary.estimated_minutes} min</span>
          <Link to="/labs/$key" params={{ key: summary.item_key }}>
            Open the lab
          </Link>
        </span>
      </div>
      {lab.isPending ? <Spinner label="Opening the lab" /> : null}
      {lab.data && summary.verifier ? <VerifiedLab lab={lab.data} timeZone={timeZone} /> : null}
      {lab.data && !summary.verifier ? (
        <div className="prose">
          <div className="cost-warning">
            <strong>Cost warning.</strong> <Markdown inline>{lab.data.cost_warning_md}</Markdown>
          </div>
          <h4>Goals</h4>
          <Markdown>{lab.data.goals_md}</Markdown>
          <h4>Steps</h4>
          <Markdown>{lab.data.steps_md}</Markdown>
          <h4>Expected observations</h4>
          <Markdown>{lab.data.expected_observations_md}</Markdown>
        </div>
      ) : null}
    </article>
  );
}

/** The lesson's "Do it" step: its labs, inline. Nothing when the lesson names none. */
export function DoIt({ labs, timeZone }: { labs: LabSummary[]; timeZone: string }) {
  if (labs.length === 0) return null;
  return (
    <section className="stack" aria-label="Do it">
      <h2>Do it</h2>
      {labs.map((lab) => (
        <DoItLab key={lab.item_key} summary={lab} timeZone={timeZone} />
      ))}
    </section>
  );
}
