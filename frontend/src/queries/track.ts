import { queryOptions } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TrackView } from "@/lib/types";
import { studyKeys } from "@/queries/study";

export const trackQueryOptions = () =>
  queryOptions({ queryKey: studyKeys.track, queryFn: () => api<TrackView>("/api/track") });
