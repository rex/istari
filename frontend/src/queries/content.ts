import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ContentItemDetail, ContentItemSummary, ImportReportView } from "@/lib/types";

/** Query keys shared by the per-resource modules (lessons, review, labs, progress). */
export const contentKeys = {
  lessons: ["lessons"] as const,
  lesson: (key: string) => ["lessons", key] as const,
  due: ["reviews", "due"] as const,
  cards: ["reviews", "cards"] as const,
  progress: ["progress"] as const,
  labs: ["labs"] as const,
  lab: (key: string) => ["labs", key] as const,
  items: (kind?: string) => ["content", "items", kind ?? "all"] as const,
  item: (key: string) => ["content", "item", key] as const,
  packs: ["content", "packs"] as const,
  notes: (itemKey?: string) => ["notes", itemKey ?? "all"] as const,
};

export const contentItemsQueryOptions = (kind?: string) =>
  queryOptions({
    queryKey: contentKeys.items(kind),
    queryFn: () =>
      api<{ items: ContentItemSummary[]; total: number }>(
        `/api/content/items${kind ? `?kind=${kind}` : ""}`,
      ),
  });
export const contentItemQueryOptions = (key: string) =>
  queryOptions({
    queryKey: contentKeys.item(key),
    queryFn: () => api<ContentItemDetail>(`/api/content/items/${key}`),
  });
export const packsQueryOptions = () =>
  queryOptions({
    queryKey: contentKeys.packs,
    queryFn: () => api<Record<string, unknown>[]>("/api/content/packs"),
  });

export function useContentMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => void queryClient.invalidateQueries({ queryKey: ["content"] });
  const importPack = useMutation({
    mutationFn: (input: { pack: unknown; dry_run: boolean }) =>
      api<ImportReportView>("/api/content/import", { method: "POST", body: input }),
    onSuccess: (_report, variables) => {
      if (!variables.dry_run) {
        invalidate();
        void queryClient.invalidateQueries();
      }
    },
  });
  const updateItem = useMutation({
    mutationFn: (input: { key: string; item: Record<string, unknown> }) =>
      api<ContentItemDetail>(`/api/content/items/${input.key}`, {
        method: "PUT",
        body: { item: input.item },
      }),
    onSuccess: invalidate,
  });
  const setFlags = useMutation({
    mutationFn: (input: { key: string; status?: string; user_approved?: boolean }) =>
      api<ContentItemDetail>(`/api/content/items/${input.key}/flags`, {
        method: "PATCH",
        body: { status: input.status, user_approved: input.user_approved },
      }),
    onSuccess: invalidate,
  });
  return { importPack, updateItem, setFlags };
}
