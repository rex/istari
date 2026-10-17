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

  it("places a lesson's figure where the body puts it, with its caption", () => {
    const figure = {
      key: "fig-one",
      title: "Figure one",
      caption_md: "A **box**, which is the thing.",
      alt: "A box",
      url: "/api/figures/fig-one.svg",
      objectives: [{ code: "1.1", title: "Objective 1.1", domain_code: "1" }],
    };
    const { container } = render(
      <Markdown figures={[figure]}>
        {"Before.\n\n![A box](figure:fig-one)\n\nAfter. ![other](figure:fig-unknown)"}
      </Markdown>,
    );
    const image = screen.getByRole("img", { name: "A box" });
    expect(image).toHaveAttribute("src", "/api/figures/fig-one.svg");
    expect(image.closest("figure")).not.toBeNull();
    expect(image.closest("p")).toBeNull();
    expect(container.querySelector("figcaption")?.textContent).toContain("Figure one.");
    expect(container.querySelector("figcaption strong")?.textContent).toBe("box");
    expect(container.querySelector("figcaption")?.textContent).toContain("1.1");
    // A figure the lesson does not carry is left as it was written, never a broken image.
    expect(container.querySelectorAll("img")).toHaveLength(1);
    expect(container.textContent).toContain("After.");
  });
});
