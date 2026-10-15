import { Badge } from "@/components/ui/Badge";
import { clusterChip } from "@/lib/labs";
import type { VerifierStateView } from "@/lib/types-labs";

export function LabClusterChip({ state }: { state: VerifierStateView }) {
  const chip = clusterChip(state);
  return (
    <div className="lab-chip" role="status">
      <Badge tone={chip.tone}>
        <span className={`lab-chip__dot lab-chip__dot--${chip.tone}`} aria-hidden="true" />
        {chip.label}
      </Badge>
      {chip.detail ? <span className="lab-chip__detail">{chip.detail}</span> : null}
    </div>
  );
}

/** The task as the backend states it, fetched live and attributed. Never stored by Istari. */
export function LabTask({ state }: { state: VerifierStateView }) {
  const { task, spec } = state;
  if (!task) {
    return (
      <section className="card labtask labtask--empty" aria-labelledby="labtask-title">
        <p className="card__eyebrow">Task · {spec.profile}</p>
        <h2 id="labtask-title">Task text is not available</h2>
        <p className="muted">
          {state.message ??
            "The lab cluster has not answered yet. The task text comes from it, live."}
        </p>
      </section>
    );
  }
  return (
    <section className="card labtask" aria-labelledby="labtask-title">
      <p className="card__eyebrow">
        Task · {spec.profile} · weight {task.weight}
        {task.requires ? ` · needs the ${task.requires} install` : ""}
      </p>
      <h2 id="labtask-title" className="labtask__title">
        {task.title}
      </h2>
      {task.context ? <p className="labtask__context">{task.context}</p> : null}
      <p className="labtask__desc">{task.description}</p>
      {task.hint ? (
        <details className="disclosure labtask__hint">
          <summary>Show the hint</summary>
          <p className="labtask__desc">{task.hint}</p>
        </details>
      ) : null}
      <p className="labtask__attribution">{state.attribution}</p>
    </section>
  );
}
