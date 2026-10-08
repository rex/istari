import { queryOptions } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { HealthView } from "@/lib/types";

/** Public (no session needed): which build the API is running. Polled slowly so a deploy shows. */
export const healthQueryOptions = () =>
  queryOptions({
    queryKey: ["health"],
    queryFn: () => api<HealthView>("/api/health"),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: false,
  });
