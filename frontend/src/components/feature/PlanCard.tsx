import type { PlanBlockView } from "@/lib/types";

const KIND_LABEL: Record<PlanBlockView["kind"], string> = {
  resume: "Resume",
  review: "Review",
  practice: "Practice",
  lesson: "Read",
};

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
              <span className="badge badge--gold">{KIND_LABEL[block.kind]}</span> {block.label}
            </div>
            <div className="plan__reason">{block.reason}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
