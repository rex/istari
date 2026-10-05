import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "@/lib/Markdown";
import { safeUrl } from "@/lib/safe-url";

describe("<Markdown />", () => {
  it("never executes or renders raw HTML", () => {
    const { container } = render(
      <Markdown>
        {'Hello <script>window.pwned = true</script> <img src=x onerror="alert(1)">'}
      </Markdown>,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect((window as unknown as { pwned?: boolean }).pwned).toBeUndefined();
    expect(container.textContent).toContain("Hello");
  });

  it("neutralises javascript: links and keeps https ones", () => {
    render(
      <Markdown>{"[bad](javascript:alert(1)) and [good](https://docs.aws.amazon.com/)"}</Markdown>,
    );
    const good = screen.getByRole("link", { name: "good" });
    expect(good).toHaveAttribute("href", "https://docs.aws.amazon.com/");
    expect(good).toHaveAttribute("rel", "noopener noreferrer");
    const bad = screen.getByText("bad");
    expect(bad.getAttribute("href") ?? "").not.toContain("javascript:");
  });

  it("safeUrl allows http(s), mailto, relative and fragments only", () => {
    expect(safeUrl("https://x.test/a")).toBe("https://x.test/a");
    expect(safeUrl("mailto:a@b.c")).toBe("mailto:a@b.c");
    expect(safeUrl("#top")).toBe("#top");
    expect(safeUrl("/learn")).toBe("/learn");
    expect(safeUrl("docs/page")).toBe("docs/page");
    expect(safeUrl("javascript:alert(1)")).toBe("");
    expect(safeUrl("data:text/html,hi")).toBe("");
  });

  it("renders GFM tables and code", () => {
    const { container } = render(
      <Markdown>{"| a | b |\n|---|---|\n| 1 | 2 |\n\n`code`"}</Markdown>,
    );
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector("code")?.textContent).toBe("code");
  });
});
