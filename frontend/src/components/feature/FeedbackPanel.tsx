import { Button } from "@/components/ui/Button";
import { Markdown } from "@/lib/Markdown";
import type { SessionItemView } from "@/lib/types";

interface FeedbackPanelProps {
  item: SessionItemView;
  onMakeCard?: () => void;
  cardBusy?: boolean;
}

/** Why the right answer is right, why each distractor is wrong, and where that comes from. */
export function FeedbackPanel({ item, onMakeCard, cardBusy = false }: FeedbackPanelProps) {
  const feedback = item.feedback;
  const answer = item.answer;
  if (!feedback || !answer) return null;
  const optionText = new Map(item.options.map((o) => [o.id, o.text_md]));
  const isCorrect = answer.is_correct === true;
  const confidentMiss = !isCorrect && answer.confidence === "confident";

  return (
    <section className="feedback" aria-live="polite">
      <p
        className={`feedback__verdict ${isCorrect ? "feedback__verdict--correct" : "feedback__verdict--wrong"}`}
      >
        {isCorrect ? "Correct." : "Not this time."}
        {confidentMiss ? (
          <span className="dim small"> You were confident — worth a card.</span>
        ) : null}
      </p>
      <blockquote className="feedback__constraint">
        <strong>Decisive constraint:</strong> {feedback.decisive_constraint}
      </blockquote>
      <div className="feedback__section">
        <h3>Why</h3>
        <Markdown>{feedback.explanation_md}</Markdown>
      </div>
      {Object.keys(feedback.distractor_rationales).length > 0 ? (
        <div className="feedback__section">
          <h3>Why the others are wrong</h3>
          <ul className="rationale">
            {Object.entries(feedback.distractor_rationales).map(([optionId, why]) => (
              <li key={optionId}>
                <span className="rationale__option">
                  <Markdown inline>{optionText.get(optionId) ?? optionId}</Markdown>
                </span>
                <Markdown inline>{why}</Markdown>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="feedback__section">
        <h3>Objectives</h3>
        <p className="small dim">
          {feedback.objectives.map((o) => `${o.code} ${o.title}`).join(" · ")}
        </p>
        <h3>Sources</h3>
        <ul className="sources">
          {feedback.sources.map((source) => (
            <li key={source.url}>
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                {source.title}
              </a>{" "}
              <span className="muted">(checked {source.checked_on})</span>
            </li>
          ))}
        </ul>
      </div>
      {onMakeCard && !isCorrect ? (
        <div className="feedback__section">
          <Button variant="secondary" size="sm" onClick={onMakeCard} busy={cardBusy}>
            Make a review card from this mistake
          </Button>
        </div>
      ) : null}
    </section>
  );
}
