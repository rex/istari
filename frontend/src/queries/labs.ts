import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { EvidenceView, LabSummary, LabView } from "@/lib/types";
import { contentKeys } from "@/queries/content";

export const labsQueryOptions = () =>
  queryOptions({ queryKey: contentKeys.labs, queryFn: () => api<LabSummary[]>("/api/labs") });

export const labQueryOptions = (key: string) =>
  queryOptions({ queryKey: contentKeys.lab(key), queryFn: () => api<LabView>(`/api/labs/${key}`) });

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
