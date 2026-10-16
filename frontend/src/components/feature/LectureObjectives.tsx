import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/Badge";
import { SOURCE_TONE } from "@/lib/lectures";
import { lectureObjectivesQueryOptions } from "@/queries/lectures";

/** The objectives a lecture is mapped to, as badges; nothing when the index has none. */
export function LectureObjectives({ course, path }: { course: string; path: string }) {
  const mappings = useQuery(lectureObjectivesQueryOptions(course, path));
  const shown = (mappings.data ?? []).filter((m) => m.source !== "excluded");
  if (shown.length === 0) return null;
  return (
    <p className="cluster small" aria-label="Objectives this lecture teaches">
      <span className="muted">Teaches</span>
      {shown.map((m) => (
        <Badge key={m.objective_code} tone={SOURCE_TONE[m.source]} title={m.objective_title}>
          {m.objective_code}
        </Badge>
      ))}
    </p>
  );
}
