import { describe, expect, it } from "vitest";

import { placedFigureKeys, placeFigures } from "@/lib/figures";

const figure = {
  key: "fig-vpc",
  title: "VPC",
  caption_md: "c",
  alt: "a",
  url: "/api/figures/fig-vpc.svg",
  objectives: [],
};

describe("figures in lesson Markdown", () => {
  it("lists the placed figure slugs in order, once each", () => {
    expect(placedFigureKeys("![a](figure:one) ![b](figure:two) ![c](figure:one)")).toEqual([
      "one",
      "two",
    ]);
    expect(placedFigureKeys("no figures ![x](https://x.test/i.png)")).toEqual([]);
  });

  it("rewrites a placed figure to its URL and leaves unknown slugs alone", () => {
    expect(placeFigures("![alt](figure:fig-vpc) and ![o](figure:fig-other)", [figure])).toBe(
      "![alt](/api/figures/fig-vpc.svg) and ![o](figure:fig-other)",
    );
    expect(placeFigures("![alt](figure:fig-vpc)", [])).toBe("![alt](figure:fig-vpc)");
  });
});
