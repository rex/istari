import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, newRequestId } from "@/lib/api";
import type {
  ActiveSessionView,
  AnswerResponse,
  Confidence,
  SessionKind,
  SessionMinutes,
  SessionView,
  TodayView,
} from "@/lib/types";

export const studyKeys = {
  today: (minutes?: number) => ["today", minutes ?? "default"] as const,
  todayAll: ["today"] as const,
  track: ["track"] as const,
  session: (id: number) => ["sessions", id] as const,
  active: ["sessions", "active"] as const,
  progress: ["progress"] as const,
};

export const todayQueryOptions = (minutes?: SessionMinutes) =>
  queryOptions({
    queryKey: studyKeys.today(minutes),
    queryFn: () => api<TodayView>(`/api/today${minutes ? `?minutes=${minutes}` : ""}`),
    staleTime: 15_000,
  });

export const sessionQueryOptions = (id: number) =>
  queryOptions({
    queryKey: studyKeys.session(id),
    queryFn: () => api<SessionView>(`/api/sessions/${id}`),
    staleTime: 0,
  });

export const activeSessionQueryOptions = () =>
  queryOptions({
    queryKey: studyKeys.active,
    queryFn: () => api<ActiveSessionView | null>("/api/sessions/active"),
    staleTime: 0,
  });

export interface CreateSessionInput {
  kind: SessionKind;
  minutes: SessionMinutes;
  focus: string;
  replace_active?: boolean;
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSessionInput) =>
      api<SessionView>("/api/sessions", { method: "POST", body: input }),
    onSuccess: (session) => {
      queryClient.setQueryData(studyKeys.session(session.id), session);
      void queryClient.invalidateQueries({ queryKey: studyKeys.todayAll });
      void queryClient.invalidateQueries({ queryKey: studyKeys.active });
    },
  });
}

export interface DraftInput {
  sessionId: number;
  position: number;
  selected_option_ids: string[];
  confidence: Confidence | null;
  expected_version: number;
}

export function useSaveDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, position, ...body }: DraftInput) =>
      api<SessionView>(`/api/sessions/${sessionId}/items/${position}/draft`, {
        method: "PUT",
        body,
      }),
    onSuccess: (session) => queryClient.setQueryData(studyKeys.session(session.id), session),
  });
}

export interface AnswerInput {
  sessionId: number;
  position: number;
  selected_option_ids: string[];
  confidence: Confidence | null;
  request_id?: string;
}

export function useSubmitAnswer() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: 2, // network blips: the server dedupes on request_id
    mutationFn: ({ sessionId, position, request_id, ...body }: AnswerInput) =>
      api<AnswerResponse>(`/api/sessions/${sessionId}/items/${position}/answer`, {
        method: "POST",
        body: { ...body, request_id: request_id ?? newRequestId() },
      }),
    onSuccess: (result, variables) => {
      queryClient.setQueryData<SessionView>(studyKeys.session(variables.sessionId), (old) =>
        old
          ? {
              ...old,
              version: result.session_version,
              answered_count: result.answered_count,
              status: result.status,
              items: old.items.map((item) =>
                item.position === result.item.position ? result.item : item,
              ),
            }
          : old,
      );
      void queryClient.invalidateQueries({ queryKey: studyKeys.todayAll });
      void queryClient.invalidateQueries({ queryKey: studyKeys.progress });
    },
  });
}

export function useSessionAction(action: "complete" | "abandon") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: number) =>
      api<SessionView>(`/api/sessions/${sessionId}/${action}`, { method: "POST" }),
    onSuccess: (session) => {
      queryClient.setQueryData(studyKeys.session(session.id), session);
      void queryClient.invalidateQueries({ queryKey: studyKeys.todayAll });
      void queryClient.invalidateQueries({ queryKey: studyKeys.active });
      void queryClient.invalidateQueries({ queryKey: studyKeys.progress });
    },
  });
}
