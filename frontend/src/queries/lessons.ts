import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ItemProgressView, LessonSummary, LessonView, NoteView } from "@/lib/types";
import { contentKeys } from "@/queries/content";

export const lessonsQueryOptions = () =>
  queryOptions({
    queryKey: contentKeys.lessons,
    queryFn: () => api<LessonSummary[]>("/api/lessons"),
  });

export const lessonQueryOptions = (key: string) =>
  queryOptions({
    queryKey: contentKeys.lesson(key),
    queryFn: () => api<LessonView>(`/api/lessons/${key}`),
  });

export function useLessonProgress(key: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: { position?: number; bookmarked?: boolean; completed?: boolean }) =>
      api<ItemProgressView>(`/api/lessons/${key}/progress`, { method: "PATCH", body: patch }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: contentKeys.lessons });
      void queryClient.invalidateQueries({ queryKey: ["today"] });
    },
  });
}

/** Notes attach to any content item (or none); a lesson's view embeds its notes. */
export function useNoteMutations(itemKey?: string) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["notes"] });
    if (itemKey) void queryClient.invalidateQueries({ queryKey: contentKeys.lesson(itemKey) });
  };
  const create = useMutation({
    mutationFn: (body_md: string) =>
      api<NoteView>("/api/notes", { method: "POST", body: { item_key: itemKey ?? null, body_md } }),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: (input: { id: number; body_md: string }) =>
      api<NoteView>(`/api/notes/${input.id}`, {
        method: "PATCH",
        body: { body_md: input.body_md },
      }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api<{ ok: true }>(`/api/notes/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}
