import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, setCsrfToken } from "@/lib/api";
import type { MeView, SettingsView, UserView } from "@/lib/types";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export const meQueryOptions = () =>
  queryOptions({
    queryKey: authKeys.me,
    queryFn: async () => {
      const me = await api<MeView>("/api/me");
      setCsrfToken(me.user.csrf_token);
      return me;
    },
    staleTime: 5 * 60_000,
    retry: false,
  });

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { username: string; password: string }) =>
      api<UserView>("/api/auth/login", { method: "POST", body: input }),
    onSuccess: async (user) => {
      setCsrfToken(user.csrf_token);
      await queryClient.invalidateQueries({ queryKey: authKeys.me });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ ok: true }>("/api/auth/logout", { method: "POST" }),
    onSettled: () => {
      setCsrfToken(null);
      queryClient.clear();
    },
  });
}

export interface SettingsPatch {
  timezone?: string;
  preferred_session_minutes?: 5 | 15 | 30;
  exam_date?: string | null;
  clear_exam_date?: boolean;
  daily_review_limit?: number;
  backlog_mode?: "normal" | "recovery";
  familiar_objective_codes?: string[];
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: SettingsPatch) =>
      api<SettingsView>("/api/settings", { method: "PATCH", body: patch }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

export interface OnboardingInput {
  exam_version_id: number;
  exam_date?: string | null;
  preferred_session_minutes: 5 | 15 | 30;
  familiar_objective_codes: string[];
}

export function useCompleteOnboarding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: OnboardingInput) =>
      api<SettingsView>("/api/onboarding", { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}
