/* Safe Markdown rendering. react-markdown never emits raw HTML (no rehype-raw),
   so embedded <script> or <img onerror> is rendered as text, and `javascript:`
   URLs are dropped by the url transform. Links open in a new tab with
   rel="noopener noreferrer". A lesson's figures, placed as `![alt](figure:slug)`,
   render as captioned <Figure>s in place of the paragraph that holds them. */

import type { ReactElement } from "react";
import ReactMarkdown, { type ExtraProps } from "react-markdown";
import remarkGfm from "remark-gfm";

import { Figure } from "@/components/ui/Figure";
import { placeFigures } from "@/lib/figures";
import { safeUrl } from "@/lib/safe-url";
import type { FigureView } from "@/lib/types";

interface MarkdownProps {
  children: string;
  className?: string;
  inline?: boolean;
  figures?: FigureView[];
}

/** The image URL when a paragraph holds exactly one image and nothing else. */
function soleImageUrl(node: ExtraProps["node"]): string | undefined {
  const children = node?.children ?? [];
  if (children.length !== 1) return undefined;
  const only = children[0];
  if (!only || only.type !== "element" || only.tagName !== "img") return undefined;
  const src = only.properties.src;
  return typeof src === "string" ? src : undefined;
}

export function Markdown({
  children,
  className,
  inline = false,
  figures = [],
}: MarkdownProps): ReactElement {
  const byUrl = new Map(figures.map((figure) => [figure.url, figure]));
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
        img: ({ src, alt }) => {
          const url = typeof src === "string" ? src : "";
          // A URL the transform dropped, or a figure the lesson does not carry: the alt
          // text in its place, never a broken image.
          if (!url) return <span className="muted">[{alt}]</span>;
          return <img src={url} alt={alt ?? ""} loading="lazy" />;
        },
        p: ({ node, children: inner }) => {
          const url = soleImageUrl(node);
          const figure = url ? byUrl.get(url) : undefined;
          if (figure) {
            return (
              <Figure figure={figure} caption={<Markdown inline>{figure.caption_md}</Markdown>} />
            );
          }
          return inline ? <>{inner}</> : <p>{inner}</p>;
        },
      }}
    >
      {placeFigures(children, figures)}
    </ReactMarkdown>
  );
  if (inline) return <span className={className}>{content}</span>;
  return <div className={className ?? "prose"}>{content}</div>;
}
