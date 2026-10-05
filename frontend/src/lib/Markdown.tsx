/* Safe Markdown rendering. react-markdown never emits raw HTML (no rehype-raw),
   so embedded <script> or <img onerror> is rendered as text, and `javascript:`
   URLs are dropped by the url transform. Links open in a new tab with
   rel="noopener noreferrer". */

import type { ReactElement } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { safeUrl } from "@/lib/safe-url";

interface MarkdownProps {
  children: string;
  className?: string;
  inline?: boolean;
}

export function Markdown({ children, className, inline = false }: MarkdownProps): ReactElement {
  const content = (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      urlTransform={safeUrl}
      components={{
        a: ({ href, children: linkChildren }) => (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {linkChildren}
          </a>
        ),
        ...(inline ? { p: ({ children: inner }) => <>{inner}</> } : {}),
      }}
    >
      {children}
    </ReactMarkdown>
  );
  if (inline) return <span className={className}>{content}</span>;
  return <div className={className ?? "prose"}>{content}</div>;
}
