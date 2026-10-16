import { queryOptions } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { CourseComparisonView } from "@/lib/types-comparison";
import { lectureKeys } from "@/queries/lectures";

/** Under the lecture-index key, so a rebuild or a review decision refreshes it too. */
export const courseComparisonQueryOptions = () =>
  queryOptions({
    queryKey: [...lectureKeys.all, "courses"] as const,
    queryFn: () => api<CourseComparisonView>("/api/lecture-index/courses"),
    staleTime: 30_000,
    // While the share is being scanned the rows are incomplete; poll until it ends.
    refetchInterval: (query) => (query.state.data?.scanning ? 2000 : false),
  });
