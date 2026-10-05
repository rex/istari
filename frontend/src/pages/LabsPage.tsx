import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { labsQueryOptions } from "@/queries/labs";

export default function LabsPage() {
  const labs = useQuery(labsQueryOptions());
  if (labs.isPending) return <Spinner label="Loading lab briefs" />;
  if (labs.isError)
    return <StateBlock tone="error" title="Could not load labs" body={labs.error.message} />;
  return (
    <div className="stack">
      <div className="page-head">
        <h1>Labs</h1>
        <p>
          Guided briefs you run by hand in your own account. Istari never provisions anything and
          never assumes a lab is free.
        </p>
      </div>
      <div className="lesson-list">
        {labs.data.map((lab) => (
          <Link
            key={lab.item_key}
            to="/labs/$key"
            params={{ key: lab.item_key }}
            className="card card--quiet lesson-row"
          >
            <span>
              <span className="lesson-row__title">{lab.title}</span>
              <span className="lesson-row__meta">
                ~{lab.estimated_minutes} min · {lab.objectives.map((o) => o.code).join(", ")}
              </span>
            </span>
            <span>
              {lab.evidence_count > 0 ? (
                <Badge tone="success">{lab.evidence_count} evidence note(s)</Badge>
              ) : (
                <Badge>not started</Badge>
              )}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
