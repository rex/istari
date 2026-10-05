import type { ReactNode } from "react";

interface StateBlockProps {
  title: string;
  body?: ReactNode;
  tone?: "neutral" | "error" | "success";
  action?: ReactNode;
}

/** Empty / error / done states that say what is true and what to do next. */
export function StateBlock({ title, body, tone = "neutral", action }: StateBlockProps) {
  return (
    <section className={`state state--${tone}`} role={tone === "error" ? "alert" : undefined}>
      <h2 className="state__title">{title}</h2>
      {body ? <div className="state__body">{body}</div> : null}
      {action ? <div className="state__action">{action}</div> : null}
    </section>
  );
}
