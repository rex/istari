/* Figures in lesson Markdown. A lesson places one of its figures with
   `![alt](figure:slug)`; before rendering, the reference becomes the figure's
   URL so the renderer can match the image to the figure and show its caption.
   The server validates the same syntax (`placed_figures` in the pack schema). */

import type { FigureView } from "@/lib/types";

const FIGURE_REF = /\]\(figure:([a-z0-9][a-z0-9-]{1,98})\)/g;

/** The figure slugs a body places inline, in order, each once. */
export function placedFigureKeys(markdown: string): string[] {
  const keys: string[] = [];
  for (const match of markdown.matchAll(FIGURE_REF)) {
    const slug = match[1];
    if (slug && !keys.includes(slug)) keys.push(slug);
  }
  return keys;
}

/** `![alt](figure:slug)` → `![alt](<figure url>)`; a slug the lesson does not carry is left as is. */
export function placeFigures(markdown: string, figures: FigureView[]): string {
  if (figures.length === 0) return markdown;
  const urls = new Map(figures.map((figure) => [figure.key, figure.url]));
  return markdown.replace(FIGURE_REF, (whole: string, slug: string) => {
    const url = urls.get(slug);
    return url ? `](${url})` : whole;
  });
}
