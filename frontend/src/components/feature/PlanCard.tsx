import type { PlanBlockView } from "@/lib/types";

const KIND_LABEL: Record<PlanBlockView["kind"], string> = {
  resume: "Resume",
  review: "Review",
  practice: "Practice",
  lab: "Lab",
  lesson: "Read",
  lecture: "Watch",
};

/** The planner prefixes a label with its kind ("Lab: …"); the badge already says it. */
function withoutKind(label: string, kind: PlanBlockView["kind"]): string {
  const prefix = `${KIND_LABEL[kind]}:`;
  const bare = label.startsWith(prefix) ? label.slice(prefix.length).trim() : label;
  return bare === KIND_LABEL[kind] ? "" : bare;
}

export function PlanBlocks({ blocks }: { blocks: PlanBlockView[] }) {
  if (blocks.length === 0) return null;
  return (
    <ol className="plan list-reset" aria-label="Session plan">
      {blocks.map((block, index) => (
        <li key={`${block.kind}-${index}`} className="plan__block">
          <span className="plan__count" aria-hidden="true">
            {block.count}
          </span>
          <div>
            <div className="plan__label">
              <span className="badge badge--gold">{KIND_LABEL[block.kind]}</span>{" "}
              {withoutKind(block.label, block.kind)}
            </div>
            <div className="plan__reason">{block.reason}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
