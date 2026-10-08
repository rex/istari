import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CatalogStatus,
  CoursesView,
  CourseView,
  LectureProgressView,
} from "@/lib/types-watch";

export const courseKeys = {
  all: ["courses"] as const,
  one: (slug: string) => ["courses", slug] as const,
};

export const mediaUrl = (slug: string, path: string) =>
  `/api/courses/${encodeURIComponent(slug)}/media?path=${encodeURIComponent(path)}`;
export const captionsUrl = (slug: string, path: string) =>
  `/api/courses/${encodeURIComponent(slug)}/captions?path=${encodeURIComponent(path)}`;

export const coursesQueryOptions = () =>
  queryOptions({
    queryKey: courseKeys.all,
    queryFn: () => api<CoursesView>("/api/courses"),
    // While the share is being scanned, poll until the listing fills in.
    refetchInterval: (query) => (query.state.data?.status.scanning ? 3000 : false),
  });

export const courseQueryOptions = (slug: string) =>
  queryOptions({
    queryKey: courseKeys.one(slug),
    queryFn: () => api<CourseView>(`/api/courses/${encodeURIComponent(slug)}`),
    staleTime: 0,
  });

export function useRefreshCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<CatalogStatus>("/api/courses/refresh", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: courseKeys.all }),
  });
}

export interface ProgressInput {
  lecture_path: string;
  position_seconds: number;
  duration_seconds?: number | undefined;
  completed?: boolean;
}

/** Position saves are frequent and quiet: nothing is invalidated until a lecture completes. */
export function useSaveLectureProgress(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProgressInput) =>
      api<LectureProgressView>(`/api/courses/${encodeURIComponent(slug)}/progress`, {
        method: "PUT",
        body: input,
      }),
    onSuccess: (saved) => {
      if (saved.completed_at) void queryClient.invalidateQueries({ queryKey: courseKeys.all });
    },
  });
}
