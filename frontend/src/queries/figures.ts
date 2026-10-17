import { queryOptions } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { FigureView } from "@/lib/types";

export const figureKeys = {
  all: ["figures"] as const,
  lecture: (slug: string, path: string) => ["figures", "lecture", slug, path] as const,
};

/** The figures of the objectives a lecture is mapped to, for the player's "See it" rail. */
export const lectureFiguresQueryOptions = (slug: string, path: string) =>
  queryOptions({
    queryKey: figureKeys.lecture(slug, path),
    queryFn: () =>
      api<FigureView[]>(
        `/api/figures/lecture/${encodeURIComponent(slug)}?path=${encodeURIComponent(path)}`,
      ),
    staleTime: 60_000,
  });
