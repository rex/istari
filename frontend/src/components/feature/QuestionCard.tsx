import { Markdown } from "@/lib/Markdown";
import type { Confidence, SessionItemView } from "@/lib/types";

interface QuestionCardProps {
  item: SessionItemView;
  total: number;
  selected: string[];
  onToggle: (optionId: string) => void;
  confidence: Confidence | null;
  onConfidence: (value: Confidence | null) => void;
  locked: boolean;
}

const CONFIDENCE: { value: Confidence; label: string }[] = [
  { value: "guessing", label: "Guessing" },
  { value: "uncertain", label: "Uncertain" },
  { value: "confident", label: "Confident" },
];

/** Options are shown in the server's stored order; positions are display-only. */
export function QuestionCard({
  item,
  total,
  selected,
  onToggle,
  confidence,
  onConfidence,
  locked,
}: QuestionCardProps) {
  const feedback = item.feedback;
  const correct = new Set(feedback?.correct_option_ids ?? []);
  const answered = new Set(item.answer?.selected_option_ids ?? selected);
  const instruction =
    item.select_count === 1 ? "Choose one" : `Choose ${item.select_count} — all must be right`;

  return (
    <section className="question" aria-labelledby={`q-${item.position}`}>
      <div className="question__meta">
        <span>
          Question {item.position} of {total}
        </span>
        <span>{item.objectives.map((o) => `${o.code}`).join(" · ")}</span>
      </div>
      <h2 id={`q-${item.position}`} className="sr-only">
        Question {item.position}
      </h2>
      <div className="question__stem">
        <Markdown>{item.stem_md}</Markdown>
      </div>
      <p className="question__instruction">{instruction}</p>
      <ul className="options" role={item.select_count === 1 ? "radiogroup" : "group"}>
        {item.options.map((option, index) => {
          const isSelected = answered.has(option.id);
          let state = "";
          if (feedback) {
            if (correct.has(option.id)) state = "is-correct";
            else if (isSelected) state = "is-wrong";
          } else if (isSelected) state = "is-selected";
          return (
            <li key={option.id}>
              <button
                type="button"
                className={`option ${state}`}
                role={item.select_count === 1 ? "radio" : "checkbox"}
                aria-checked={isSelected}
                disabled={locked}
                onClick={() => onToggle(option.id)}
              >
                <span className="option__key" aria-hidden="true">
                  {index + 1}
                </span>
                <span className="option__text">
                  <Markdown>{option.text_md}</Markdown>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {!locked ? (
        <div className="confidence" role="group" aria-label="How sure are you?">
          <span className="confidence__label">How sure are you? (optional)</span>
          {CONFIDENCE.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`btn btn--sm ${confidence === option.value ? "btn--primary" : "btn--ghost"}`}
              aria-pressed={confidence === option.value}
              onClick={() => onConfidence(confidence === option.value ? null : option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
