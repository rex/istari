import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { EvidenceView, LabSummary, LabView } from "@/lib/types";
import type { CheckResponse, SetupResponse, VerifierStateView } from "@/lib/types-labs";
import { contentKeys } from "@/queries/content";

export const labsQueryOptions = () =>
  queryOptions({ queryKey: contentKeys.labs, queryFn: () => api<LabSummary[]>("/api/labs") });

export const labQueryOptions = (key: string) =>
  queryOptions({ queryKey: contentKeys.lab(key), queryFn: () => api<LabView>(`/api/labs/${key}`) });

/** The backend's live view of a verified lab. Short stale time: the cluster changes under us. */
export const verifierQueryOptions = (key: string) =>
  queryOptions({
    queryKey: contentKeys.verifier(key),
    queryFn: () => api<VerifierStateView>(`/api/labs/${key}/verifier`),
    staleTime: 10_000,
    retry: false,
  });

/** Set up the task on the backend, or ask it to grade. Both refresh everything the verdict touches. */
export function useVerifierActions(labKey: string) {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: contentKeys.verifier(labKey) });
    void queryClient.invalidateQueries({ queryKey: contentKeys.lab(labKey) });
    void queryClient.invalidateQueries({ queryKey: contentKeys.labs });
    void queryClient.invalidateQueries({ queryKey: contentKeys.progress });
    void queryClient.invalidateQueries({ queryKey: ["today"] });
  };
  const setup = useMutation({
    mutationFn: () => api<SetupResponse>(`/api/labs/${labKey}/setup`, { method: "POST" }),
    onSettled: refresh,
  });
  const check = useMutation({
    mutationFn: () => api<CheckResponse>(`/api/labs/${labKey}/check`, { method: "POST" }),
    onSettled: refresh,
  });
  return { setup, check };
}

export function useEvidenceMutations(labKey: string) {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: contentKeys.lab(labKey) });
    void queryClient.invalidateQueries({ queryKey: contentKeys.labs });
  };
  const add = useMutation({
    mutationFn: (body_md: string) =>
      api<EvidenceView>(`/api/labs/${labKey}/evidence`, { method: "POST", body: { body_md } }),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: (input: { id: number; body_md: string }) =>
      api<EvidenceView>(`/api/labs/evidence/${input.id}`, {
        method: "PATCH",
        body: { body_md: input.body_md },
      }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api<{ ok: true }>(`/api/labs/evidence/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
  return { add, update, remove };
}
