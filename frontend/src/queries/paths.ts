import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ObjectivePathView, PathDecision, PathsView } from "@/lib/types-paths";

export const pathKeys = {
  all: ["paths"] as const,
  summaries: ["paths", "summaries"] as const,
  objective: (code: string) => ["paths", "objective", code] as const,
};

export const pathsQueryOptions = () =>
  queryOptions({
    queryKey: pathKeys.summaries,
    queryFn: () => api<PathsView>("/api/paths"),
    staleTime: 30_000,
  });

export const objectivePathQueryOptions = (code: string) =>
  queryOptions({
    queryKey: pathKeys.objective(code),
    queryFn: () => api<ObjectivePathView>(`/api/paths/${encodeURIComponent(code)}`),
    staleTime: 30_000,
  });

export function usePathMutations() {
  const queryClient = useQueryClient();
  const rebuild = useMutation({
    mutationFn: () => api<PathsView>("/api/paths/rebuild", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pathKeys.all }),
  });
  const decide = useMutation({
    mutationFn: ({ code, ...decision }: PathDecision & { code: string }) =>
      api<ObjectivePathView>(`/api/paths/${encodeURIComponent(code)}`, {
        method: "POST",
        body: decision,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: pathKeys.all }),
  });
  return { rebuild, decide };
}
