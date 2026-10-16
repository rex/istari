/* Presentation helpers for the lecture index (kept out of component files for fast refresh). */

import type { MappingSource } from "@/lib/types-lectures";

/** Badge tone per mapping source: the owner's pins are gold, title rules read as certain,
 *  ranked matches as information, exclusions as danger. */
export const SOURCE_TONE: Record<MappingSource, "gold" | "success" | "info" | "danger"> = {
  pinned: "gold",
  rule: "success",
  lexical: "info",
  excluded: "danger",
};
