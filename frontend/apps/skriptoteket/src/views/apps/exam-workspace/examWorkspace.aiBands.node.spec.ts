// @vitest-environment node
/**
 * Exam workspace toolbar AI group: band rules, sticky pin and reserved scrollbar.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D7):
 *   The workspace stylesheet keys the AI group's composition only to the
 *   viewport bands, `data-side` and the pointer kind, never to the column
 *   width, so a column drag never changes the toolbar. Desktop without a side
 *   panel shows the suggested type name; the tablet band and any open side
 *   panel show the type glyph only; phones and every coarse pointer hide the
 *   group and show its menu rows instead. While the bar overflows, the group
 *   stays pinned at its right edge, and the question-text toolbar always
 *   reserves the horizontal scrollbar's height.
 *
 * Relationships:
 *   - Reads `examWorkspace.css` from disk as text, because a unit test cannot
 *     evaluate media queries; it runs in the node environment so `node:fs` is
 *     typed by the node project (`tsconfig.node.json`).
 *   - The rendered class is proved through the two hosts that carry it
 *     (`ExamWorkspaceBodyEditor` yes, an instruction editor no) by the jsdom
 *     half, `examWorkspace.aiBands.spec.ts`.
 *   - The classes themselves belong to `ExamWorkspaceQuestionAiGroup.vue`;
 *     this half reads them from the stylesheet and never renders that
 *     component.
 */

import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

/** The stylesheet as text. Vitest stubs CSS imports (empty, `?raw` included), so the file is read from disk; a unit test cannot evaluate media queries. */
const stylesheet = readFileSync(new URL("./examWorkspace.css", import.meta.url), "utf8");

interface StyleBlock {
  prelude: string;
  body: string;
}

/** The blocks at one nesting level of a stylesheet fragment, comments removed. */
function childBlocks(text: string): StyleBlock[] {
  const source = text.replace(/\/\*[\s\S]*?\*\//g, "");
  const blocks: StyleBlock[] = [];
  let cursor = 0;
  while (cursor < source.length) {
    const open = source.indexOf("{", cursor);
    if (open < 0) {
      break;
    }
    let depth = 1;
    let close = open + 1;
    while (close < source.length && depth > 0) {
      if (source[close] === "{") {
        depth += 1;
      } else if (source[close] === "}") {
        depth -= 1;
      }
      close += 1;
    }
    blocks.push({ prelude: source.slice(cursor, open).trim(), body: source.slice(open + 1, close - 1) });
    cursor = close;
  }
  return blocks;
}

/** Every rule block, with media and other at-rules flattened away. */
function leafRules(text: string): StyleBlock[] {
  return childBlocks(text).flatMap((block) =>
    block.prelude.startsWith("@") ? leafRules(block.body) : [block],
  );
}

/** The declarations of every rule in `scope` whose selector list names `selector` exactly. */
function declarations(scope: string, selector: string): string[] {
  return childBlocks(scope)
    .filter((block) => block.prelude.split(",").map((part) => part.trim()).includes(selector))
    .map((block) => block.body.replace(/\s+/g, " ").trim());
}

/** The declarations of one selector in one scope, joined for substring assertions. */
function declarationText(scope: string, selector: string): string {
  return declarations(scope, selector).join(" ");
}

/** The single top-level media block whose prelude names every keyword. */
function mediaBlock(...keywords: string[]): StyleBlock {
  const matches = childBlocks(stylesheet).filter(
    (block) => block.prelude.startsWith("@media") && keywords.every((keyword) => block.prelude.includes(keyword)),
  );
  expect(matches).toHaveLength(1);
  return matches[0]!;
}

/** Every `@media` block that hides `selector`, as its prelude. */
function mediaPreludesHiding(selector: string): string[] {
  return childBlocks(stylesheet)
    .filter((block) => block.prelude.startsWith("@media"))
    .filter((block) => declarationText(block.body, selector).includes("display: none"))
    .map((block) => block.prelude);
}

describe("the toolbar AI group's band rules", () => {
  it("keys the reserved scrollbar to the question-text toolbar only", () => {
    const questionBar = declarationText(stylesheet, ".xw-toolbar--question");

    expect(questionBar).toContain("overflow-x: scroll");
    expect(declarationText(stylesheet, ".xw-toolbar")).toContain("overflow-x: auto");
  });

  it("pins the group at the overflowing bar's right edge over an opaque bar background", () => {
    const group = declarationText(stylesheet, ".qai");

    expect(group).toContain("position: sticky");
    expect(group).toContain("right: 0");
    expect(group).toContain("padding-left: var(--huleedu-space-1)");
    expect(group).toContain("background:");
    // The bar paints `--huleedu-navy-02` over the content surface, and that tint is
    // translucent; the pin must reproduce the composite or the tools show through.
    expect(group).toContain("--huleedu-navy-02");
    expect(group).toContain("--huleedu-surface-content");
  });

  it("shows the type name only on desktop with no side panel", () => {
    expect(mediaPreludesHiding(".qai__name")).toEqual(["@media (max-width: 1279px)"]);
    expect(declarationText(stylesheet, ".ws[data-side] .qai__name")).toContain("display: none");
    expect(declarationText(stylesheet, ".qai__name")).not.toContain("display: none");
  });

  it("gives the glyph-only type button the box of a plain tool", () => {
    const tablet = mediaBlock("(max-width: 1279px)");

    expect(declarationText(tablet.body, ".qai__name")).toContain("display: none");
    expect(declarationText(tablet.body, ".qai__type")).toContain("padding: 0");
    expect(declarationText(stylesheet, ".ws[data-side] .qai__type")).toContain("padding: 0");
  });

  it("replaces the group with its menu rows on phones and coarse pointers", () => {
    const phone = mediaBlock("(max-width: 767px)", "(pointer: coarse)");

    expect(declarationText(stylesheet, ".qai-mi")).toContain("display: none");
    expect(declarationText(stylesheet, ".qai-mi-sep")).toContain("display: none");
    expect(mediaPreludesHiding(".qai")).toEqual(["@media (max-width: 767px), (pointer: coarse)"]);
    expect(declarationText(phone.body, ".qai")).toContain("display: none");
    expect(declarationText(phone.body, ".qai-mi")).toContain("display: flex");
    expect(declarationText(phone.body, ".qai-mi-sep")).toContain("display: block");
    expect(declarationText(phone.body, ".qai-mi-sep")).toContain("background: var(--huleedu-surface-divider)");
  });

  it("never keys the group to a container query or a column-size variable", () => {
    const qaiContainerRules = childBlocks(stylesheet).filter(
      (block) => block.prelude.startsWith("@container") && block.body.includes("qai"),
    );
    expect(qaiContainerRules).toEqual([]);

    const qaiRules = leafRules(stylesheet).filter((block) => block.prelude.includes("qai"));
    expect(qaiRules.length).toBeGreaterThan(0);
    for (const rule of qaiRules) {
      expect(rule.body).not.toContain("--xw-list-size");
      expect(rule.body).not.toContain("--xw-side-size");
    }
  });
});
