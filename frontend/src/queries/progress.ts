import { queryOptions } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ProgressView } from "@/lib/types";
import { contentKeys } from "@/queries/content";

export const progressQueryOptions = () =>
  queryOptions({
    queryKey: contentKeys.progress,
    queryFn: () => api<ProgressView>("/api/progress"),
  });
