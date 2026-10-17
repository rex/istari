import type { ReactNode } from "react";

import type { FigureView } from "@/lib/types";

/** A drawing of the thing, with its caption (the decision rule) and the task statements it
    serves. The image opens full size in a new tab. */
export function Figure({ figure, caption }: { figure: FigureView; caption: ReactNode }) {
  return (
    <figure className="figure">
      <a
        className="figure__frame"
        href={figure.url}
        target="_blank"
        rel="noopener noreferrer"
        title="Open full size"
      >
        <img src={figure.url} alt={figure.alt} loading="lazy" />
      </a>
      <figcaption className="figure__caption">
        <span className="figure__title">{figure.title}.</span> {caption}
        {figure.objectives.length > 0 ? (
          <span className="figure__meta muted">
            {" "}
            {figure.objectives.map((objective) => objective.code).join(" · ")}
          </span>
        ) : null}
      </figcaption>
    </figure>
  );
}
