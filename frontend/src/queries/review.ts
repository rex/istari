import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, newRequestId } from "@/lib/api";
import type { CardView, DueResponse, RateResponse } from "@/lib/types";
import { contentKeys } from "@/queries/content";

export const dueQueryOptions = (limit?: number) =>
  queryOptions({
    queryKey: [...contentKeys.due, limit ?? "all"],
    queryFn: () => api<DueResponse>(`/api/reviews/due${limit ? `?limit=${limit}` : ""}`),
    staleTime: 0,
  });

export const cardsQueryOptions = () =>
  queryOptions({
    queryKey: contentKeys.cards,
    queryFn: () => api<{ cards: CardView[]; total: number }>("/api/reviews/cards"),
  });

export function useRateCard() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: 2,
    mutationFn: (input: {
      cardId: number;
      rating: 1 | 2 | 3 | 4;
      duration_ms?: number;
      request_id?: string;
    }) =>
      api<RateResponse>(`/api/reviews/cards/${input.cardId}/rate`, {
        method: "POST",
        body: {
          rating: input.rating,
          duration_ms: input.duration_ms,
          request_id: input.request_id ?? newRequestId(),
        },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["today"] });
      void queryClient.invalidateQueries({ queryKey: contentKeys.progress });
    },
  });
}

export function useCardMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["reviews"] });
    void queryClient.invalidateQueries({ queryKey: contentKeys.progress });
  };
  const create = useMutation({
    mutationFn: (input: {
      source_kind: "mistake" | "note" | "custom";
      item_key?: string;
      note_id?: number;
      front_md: string;
      back_md: string;
    }) => api<CardView>("/api/reviews/cards", { method: "POST", body: input }),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: (input: {
      cardId: number;
      front_md?: string;
      back_md?: string;
      suspended?: boolean;
    }) =>
      api<CardView>(`/api/reviews/cards/${input.cardId}`, {
        method: "PATCH",
        body: { front_md: input.front_md, back_md: input.back_md, suspended: input.suspended },
      }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (cardId: number) =>
      api<{ ok: true }>(`/api/reviews/cards/${cardId}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}
