import { useQuery } from "@tanstack/react-query";

import { Figure } from "@/components/ui/Figure";
import { Markdown } from "@/lib/Markdown";
import { lectureFiguresQueryOptions } from "@/queries/figures";

/** The pack's figures for the objectives this lecture teaches, borrowed into the player's
    rail; nothing when the lecture maps to no objective with a drawing. */
export function SeeIt({ course, path }: { course: string; path: string }) {
  const figures = useQuery(lectureFiguresQueryOptions(course, path));
  const shown = figures.data ?? [];
  if (shown.length === 0) return null;
  return (
    <section className="stack" aria-label="See it">
      <h3>See it</h3>
      {shown.map((figure) => (
        <Figure
          key={figure.key}
          figure={figure}
          caption={<Markdown inline>{figure.caption_md}</Markdown>}
        />
      ))}
    </section>
  );
}
