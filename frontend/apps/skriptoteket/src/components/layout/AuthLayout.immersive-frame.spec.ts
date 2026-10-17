/**
 * Static contract between the immersive shell frame and the game's narrow layout.
 *
 * The shell gives immersive routes a bounded frame that does not scroll; below
 * 941 px the game stacks status, cabinet and service controls, which is taller
 * than that frame. These checks read the stylesheet sources and assert that the
 * game root is then the one vertical scroll owner and that no inner layer is
 * pinned back to the frame height (which would clip Start again). jsdom does
 * not lay out CSS, so this is a source contract; the reachable Start button at
 * phone width is proven by the browser walk.
 */

import { describe, expect, it } from "vitest";

/**
 * Vitest blanks CSS imports, so the sources are read from disk. The SPA
 * tsconfig carries no Node types, so `node:fs` is imported by a string
 * specifier with the one signature this spec uses.
 */
const NODE_FS = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ NODE_FS)) as {
  readFileSync: (path: string, encoding: "utf8") => string;
};

function readSource(relativePath: string): string {
  return readFileSync(decodeURIComponent(new URL(relativePath, import.meta.url).pathname), "utf8");
}

const authLayoutSource = readSource("./AuthLayout.vue");
const fofLayoutCss = readSource("../../views/apps/styles/fof-shell-layout.css");

type CssRule = { selector: string; body: string; media: string | null };

/** Flattens a stylesheet into rules, keeping the enclosing `@media` query. */
function parseRules(css: string): CssRule[] {
  const source = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const rules: CssRule[] = [];

  function walk(text: string, media: string | null): void {
    let index = 0;
    while (index < text.length) {
      const open = text.indexOf("{", index);
      if (open === -1) {
        return;
      }
      const prelude = text.slice(index, open).trim();
      let depth = 1;
      let close = open + 1;
      while (depth > 0 && close < text.length) {
        if (text[close] === "{") depth += 1;
        if (text[close] === "}") depth -= 1;
        close += 1;
      }
      const body = text.slice(open + 1, close - 1);
      if (prelude.startsWith("@media")) {
        walk(body, prelude.replace(/^@media\s*/, ""));
      } else {
        rules.push({ selector: prelude.replace(/\s+/g, " "), body, media });
      }
      index = close;
    }
  }

  walk(source, null);
  return rules;
}

function maxWidth(media: string | null): number | null {
  const match = media?.match(/max-width:\s*(\d+)px/);
  return match ? Number(match[1]) : null;
}

/** Rules that apply at a given narrow viewport width. */
function rulesAt(rules: CssRule[], width: number): CssRule[] {
  return rules.filter((rule) => {
    const limit = maxWidth(rule.media);
    return rule.media === null || (limit !== null && width <= limit);
  });
}

function declaration(body: string, property: string): string | null {
  const match = body.match(new RegExp(`(?:^|;|\\s)${property}\\s*:\\s*([^;]+)`));
  return match ? match[1]!.trim() : null;
}

/** The last matching declaration wins, as in the cascade for equal selectors. */
function resolved(rules: CssRule[], selector: string, property: string): string | null {
  let value: string | null = null;
  for (const rule of rules) {
    if (rule.selector.split(",").map((part) => part.trim()).includes(selector)) {
      value = declaration(rule.body, property) ?? value;
    }
  }
  return value;
}

const fofRules = parseRules(fofLayoutCss);
const shellStyle = authLayoutSource.slice(authLayoutSource.indexOf("<style"));
const shellRules = parseRules(shellStyle.replace(/<\/?style[^>]*>/g, ""));

const ROOT = ".fof-game-container.fof-shell";
const INNER = [".fof-game-container .fof-ready", ".fof-game-container .fof-machine-scene"];

describe("immersive frame and narrow game scroll owner", () => {
  it("keeps the shell's immersive frame non-scrolling, so the game must own scrolling", () => {
    expect(resolved(shellRules, ".auth-main-content--immersive", "overflow")).toBe("hidden");
  });

  it.each([375, 768, 940])("makes the game root the vertical scroll owner at %i px", (width) => {
    const active = rulesAt(fofRules, width);
    expect(resolved(active, ROOT, "overflow-y")).toBe("auto");
    expect(resolved(active, ROOT, "height")).toBe("100%");
  });

  it.each([375, 768, 940])("lets the inner layers take their content height at %i px", (width) => {
    const active = rulesAt(fofRules, width);
    for (const selector of INNER) {
      expect(resolved(active, selector, "height"), selector).toBe("auto");
    }
    expect(resolved(active, ".fof-game-container .fof-ready", "grid-template-rows")).not.toMatch(
      /minmax\(0,\s*1fr\)/,
    );
  });

  it("adds no second vertical scroll owner inside the narrow game", () => {
    const owners = rulesAt(fofRules, 375).filter((rule) =>
      /overflow(-y)?\s*:\s*(auto|scroll)/.test(rule.body),
    );
    expect(owners.map((rule) => rule.selector)).toEqual([ROOT]);
  });

  it("keeps the wide cabinet bounded to the frame above 940 px", () => {
    const wide = fofRules.filter((rule) => rule.media === null);
    expect(resolved(wide, ROOT, "overflow")).toBe("hidden");
    for (const selector of INNER) {
      expect(resolved(wide, selector, "height"), selector).toBe("100%");
    }
  });
});
