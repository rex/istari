import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CourseDecision,
  IndexStatusView,
  LectureMappingView,
  ObjectiveLecturesView,
  ReviewDecision,
  ReviewLectureView,
  ReviewQueueView,
} from "@/lib/types-lectures";

export type QueueCursor = [course: string, path: string] | null;

export const lectureKeys = {
  all: ["lecture-index"] as const,
  status: ["lecture-index", "status"] as const,
  queue: (after: QueueCursor) =>
    ["lecture-index", "queue", after?.[0] ?? "", after?.[1] ?? ""] as const,
  lecture: (slug: string, path: string) => ["lecture-index", "lecture", slug, path] as const,
  objective: (code: string) => ["lecture-index", "objective", code] as const,
};

export const indexStatusQueryOptions = () =>
  queryOptions({
    queryKey: lectureKeys.status,
    queryFn: () => api<IndexStatusView>("/api/lecture-index"),
    // While a build runs, poll until it ends; the status row carries the counts.
    refetchInterval: (query) => (query.state.data?.running ? 2000 : false),
  });

export const reviewQueueQueryOptions = (after: QueueCursor) =>
  queryOptions({
    queryKey: lectureKeys.queue(after),
    queryFn: () =>
      api<ReviewQueueView>(
        after
          ? `/api/lecture-index/review?after_course=${encodeURIComponent(after[0])}&after_path=${encodeURIComponent(after[1])}`
          : "/api/lecture-index/review",
      ),
    staleTime: 0,
  });

export const lectureObjectivesQueryOptions = (slug: string, path: string) =>
  queryOptions({
    queryKey: lectureKeys.lecture(slug, path),
    queryFn: () =>
      api<LectureMappingView[]>(
        `/api/lecture-index/lectures/${encodeURIComponent(slug)}?path=${encodeURIComponent(path)}`,
      ),
    staleTime: 60_000,
  });

export const objectiveLecturesQueryOptions = (code: string) =>
  queryOptions({
    queryKey: lectureKeys.objective(code),
    queryFn: () =>
      api<ObjectiveLecturesView>(`/api/lecture-index/objectives/${encodeURIComponent(code)}`),
    staleTime: 60_000,
  });

export function useLectureIndexMutations() {
  const queryClient = useQueryClient();
  const rebuild = useMutation({
    mutationFn: () => api<IndexStatusView>("/api/lecture-index/rebuild", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: lectureKeys.all }),
  });
  const decide = useMutation({
    mutationFn: (decision: ReviewDecision) =>
      api<ReviewLectureView>("/api/lecture-index/review", { method: "POST", body: decision }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: lectureKeys.all }),
  });
  const decideCourse = useMutation({
    mutationFn: (decision: CourseDecision) =>
      api<ReviewQueueView>("/api/lecture-index/review/course", {
        method: "POST",
        body: decision,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: lectureKeys.all }),
  });
  return { rebuild, decide, decideCourse };
}
