import type { ReactNode } from "react";

type Tone = "neutral" | "gold" | "success" | "danger" | "warning" | "info";

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: Tone;
  children: ReactNode;
  title?: string;
}) {
  return (
    <span className={`badge badge--${tone}`} title={title}>
      {children}
    </span>
  );
}

const EVIDENCE_TONE: Record<string, Tone> = {
  insufficient: "neutral",
  weak: "danger",
  developing: "warning",
  solid: "success",
};

export function EvidenceBadge({ level }: { level: string }) {
  const label = level === "insufficient" ? "insufficient evidence" : level;
  return <Badge tone={EVIDENCE_TONE[level] ?? "neutral"}>{label}</Badge>;
}
