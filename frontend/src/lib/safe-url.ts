/* URL allow-list used by the Markdown renderer. Anything not http(s), mailto,
   a fragment or a relative path is dropped, so `javascript:` and `data:` never
   reach an href. */

const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

export function safeUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith("#") || trimmed.startsWith("/")) return trimmed;
  try {
    const parsed = new URL(trimmed, "https://istari.invalid/");
    if (parsed.origin === "https://istari.invalid" && !/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) {
      return trimmed; // relative path
    }
    return SAFE_PROTOCOLS.has(parsed.protocol) ? trimmed : "";
  } catch {
    return "";
  }
}
