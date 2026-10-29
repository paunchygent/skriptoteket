// @vitest-environment node
/**
 * Touch field text: one shared 16px rule, and no touch rule that shrinks a field.
 *
 * Expected behavior (TASK-SKRIPT-REP-0057):
 *   iOS WebKit zooms the page when a field whose text is smaller than 16px
 *   takes focus. `main.css` therefore holds one unlayered rule, inside
 *   `@media (pointer: coarse), (hover: none)`, that sets `font-size: 16px` on
 *   every text input, select, textarea, `contenteditable` surface and
 *   CodeMirror `.cm-content`. No stylesheet (`.css` file or `<style>` block of
 *   a `.vue` file) sets a field's font-size below 16px inside a touch media
 *   block, because that rule would shrink the field again on touch devices.
 *
 * Relationships:
 *   - Reads every stylesheet under `src` from disk as text, because Vitest
 *     stubs CSS imports and a unit test cannot evaluate media queries; it runs
 *     in the node environment so `node:fs` is typed by `tsconfig.node.json`.
 *   - The rule under test lives in `main.css`; local rules that a unit test
 *     cannot rank against it are walked in a browser.
 *   - Like `examWorkspace.aiBands.node.spec.ts`, it reads CSS as text.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC_DIR = fileURLToPath(new URL("..", import.meta.url));
const MINIMUM_PX = 16;
const TOUCH_MEDIA = /pointer\s*:\s*coarse|hover\s*:\s*none/;
const SHARED_SELECTORS = [
  "input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]):not([type=button]):not([type=submit]):not([type=reset]):not([type=color]):not([type=image])",
  "select",
  "textarea",
  '[contenteditable=""]',
  '[contenteditable="true"]',
  ".cm-content",
];

/** Design tokens that resolve below 16px, from `huleedu-design-tokens.css`. */
const SMALL_TOKENS = new Set([
  "--huleedu-text-xs",
  "--huleedu-text-sm",
  "--huleedu-type-control-value-size",
  "--huleedu-workbench-control-text",
  "--huleedu-type-field-label-size",
  "--huleedu-type-supporting-size",
  "--huleedu-type-helper-size",
]);
/** Design tokens that resolve to 16px or more. */
const LARGE_TOKENS = new Set([
  "--huleedu-text-base",
  "--huleedu-text-lg",
  "--huleedu-text-xl",
  "--huleedu-text-2xl",
]);

interface Rule {
  layers: string[];
  media: string[];
  selector: string;
  body: string;
}

interface Stylesheet {
  path: string;
  text: string;
}

function walk(dir: string): string[] {
  return readdirSync(dir, { recursive: true, encoding: "utf8" }).map((entry) => join(dir, entry));
}

/** Every `.css` file and every `<style>` block under `src`, as text. */
function readStylesheets(): Stylesheet[] {
  const sheets: Stylesheet[] = [];
  for (const path of walk(SRC_DIR)) {
    if (path.endsWith(".css")) {
      sheets.push({ path, text: readFileSync(path, "utf8") });
    } else if (path.endsWith(".vue")) {
      const source = readFileSync(path, "utf8");
      for (const match of source.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)) {
        sheets.push({ path, text: match[1] ?? "" });
      }
    }
  }
  return sheets;
}

/** Every rule of a stylesheet, with the `@media` preludes and other at-rules (such as `@layer`) that enclose it. */
function parseRules(text: string, media: string[] = [], layers: string[] = []): Rule[] {
  const source = text.replace(/\/\*[\s\S]*?\*\//g, "");
  const rules: Rule[] = [];
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
    const prelude = source.slice(cursor, open).trim().split(";").pop()?.trim() ?? "";
    const body = source.slice(open + 1, close - 1);
    if (prelude.startsWith("@media")) {
      rules.push(...parseRules(body, [...media, prelude], layers));
    } else if (prelude.startsWith("@")) {
      rules.push(...parseRules(body, media, [...layers, prelude]));
    } else if (prelude !== "") {
      rules.push({ layers, media, selector: prelude.replace(/\s+/g, " "), body });
    }
    cursor = close;
  }
  return rules;
}

/** Whether `value` is below 16px; sizes the test cannot resolve count as below, so a new form needs a decision. */
function isBelowMinimum(value: string): boolean {
  const size = value.trim();
  const token = /^var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)$/.exec(size);
  if (token) {
    const name = token[1] ?? "";
    return !LARGE_TOKENS.has(name) || SMALL_TOKENS.has(name);
  }
  const length = /^(\d*\.?\d+)(px|rem|em)$/.exec(size);
  if (length) {
    const amount = Number(length[1]);
    return (length[2] === "px" ? amount : amount * 16) < MINIMUM_PX;
  }
  return !/^(inherit|initial|unset|revert|revert-layer)$/.test(size);
}

/** The font sizes a rule body sets: `font-size`, the size inside a `font` shorthand, and `@apply text-*` utilities. */
function declaredSizes(body: string): string[] {
  const sizes: string[] = [];
  for (const match of body.matchAll(/(?<![\w-])font-size\s*:\s*([^;}]+)/g)) {
    sizes.push((match[1] ?? "").trim());
  }
  for (const match of body.matchAll(/(?<![\w-])font\s*:\s*([^;}]+)/g)) {
    const shorthand = (match[1] ?? "").trim();
    if (/^(inherit|initial|unset|revert)$/.test(shorthand)) {
      continue;
    }
    const size = /(?:^|\s)(\d*\.?\d+(?:px|rem|em)|var\([^)]*\))(?:\/\S+)?(?=\s|$)/.exec(shorthand);
    sizes.push(size?.[1] ?? shorthand);
  }
  for (const match of body.matchAll(/@apply\s+([^;}]+)/g)) {
    for (const utility of (match[1] ?? "").trim().split(/\s+/)) {
      const bare = utility.split(":").pop() ?? "";
      if (bare === "text-xs" || bare === "text-sm") {
        sizes.push(bare === "text-xs" ? "0.75rem" : "0.875rem");
      }
      const arbitrary = /^text-\[(\d*\.?\d+(?:px|rem|em))\]$/.exec(bare);
      if (arbitrary) {
        sizes.push(arbitrary[1] ?? "");
      }
    }
  }
  return sizes;
}

/** Class names that sit on an `<input>`, `<select>` or `<textarea>` in a template, so a rule on them counts as a field rule. */
function fieldClassNames(): Set<string> {
  const names = new Set<string>();
  for (const path of walk(SRC_DIR).filter((entry) => entry.endsWith(".vue"))) {
    const template = readFileSync(path, "utf8").split("<style")[0] ?? "";
    for (const tag of template.matchAll(/<(?:input|select|textarea)\b[\s\S]*?>/g)) {
      for (const attribute of tag[0].matchAll(/\sclass="([^"]*)"/g)) {
        for (const name of (attribute[1] ?? "").split(/\s+/)) {
          if (/^[a-z][\w-]*$/.test(name)) {
            names.add(name);
          }
        }
      }
    }
  }
  return names;
}

function isFieldSelector(selector: string, classNames: Set<string>): boolean {
  if (/(^|[\s>+~,(])(input|select|textarea)(?![\w-])|contenteditable|\.cm-content|ProseMirror/.test(selector)) {
    return true;
  }
  return [...selector.matchAll(/\.([\w-]+)/g)].some((match) => classNames.has(match[1] ?? ""));
}

/** Rules inside a touch media block that set a field's text below 16px, as `path: selector { size }`. */
function touchRulesShrinkingFields(sheets: Stylesheet[]): string[] {
  const classNames = fieldClassNames();
  const violations: string[] = [];
  for (const sheet of sheets) {
    for (const rule of parseRules(sheet.text)) {
      if (!rule.media.some((prelude) => TOUCH_MEDIA.test(prelude))) {
        continue;
      }
      const selectors = rule.selector.split(/,(?![^()]*\))/).map((part) => part.trim());
      if (!selectors.some((selector) => isFieldSelector(selector, classNames))) {
        continue;
      }
      for (const size of declaredSizes(rule.body).filter(isBelowMinimum)) {
        violations.push(`${sheet.path.replace(SRC_DIR, "src/")}: ${rule.media.join(" ")} ${rule.selector} { ${size} }`);
      }
    }
  }
  return violations;
}

describe("the shared touch field rule", () => {
  const mainCss = readFileSync(join(SRC_DIR, "assets", "main.css"), "utf8");
  const rules = parseRules(mainCss);

  it("sets 16px on every field selector inside the touch media query, outside any layer", () => {
    const shared = rules.filter(
      (rule) => rule.media.length === 1 && rule.media[0] === "@media (pointer: coarse), (hover: none)",
    );
    const sharedRule = shared.find((rule) => /(^|\s)select(,|$)/.test(rule.selector));

    expect(sharedRule).toBeDefined();
    expect(sharedRule?.selector.split(/,(?![^()]*\))/).map((part) => part.trim())).toEqual(SHARED_SELECTORS);
    expect(sharedRule?.body.replace(/\s+/g, " ").trim()).toBe("font-size: 16px;");
    expect(sharedRule?.layers).toEqual([]);
  });
});

describe("touch media blocks", () => {
  it("set no field text below 16px in any stylesheet under src", () => {
    expect(touchRulesShrinkingFields(readStylesheets())).toEqual([]);
  });

  it("flag a field rule below 16px inside a touch block and pass the unrelated or sufficient ones", () => {
    const sheet = (text: string): Stylesheet[] => [{ path: join(SRC_DIR, "fixture.css"), text }];

    expect(
      touchRulesShrinkingFields(
        sheet("@media (pointer: coarse) { .row select { font-size: 0.75rem; } }"),
      ),
    ).toHaveLength(1);
    expect(
      touchRulesShrinkingFields(
        sheet("@layer components { @media (hover: none) { textarea { font-size: var(--huleedu-text-sm); } } }"),
      ),
    ).toHaveLength(1);
    expect(
      touchRulesShrinkingFields(sheet("@media (pointer: coarse) { .x input { font: 13px/1.2 sans-serif; } }")),
    ).toHaveLength(1);
    expect(
      touchRulesShrinkingFields(sheet("@media (hover: none) { .cm-content { @apply text-xs; } }")),
    ).toHaveLength(1);
    expect(
      touchRulesShrinkingFields(sheet("@media (pointer: coarse) { .row select { font-size: 16px; } }")),
    ).toEqual([]);
    expect(
      touchRulesShrinkingFields(sheet("@media (pointer: coarse) { .row p { font-size: 0.75rem; } }")),
    ).toEqual([]);
    expect(
      touchRulesShrinkingFields(sheet("@media (min-width: 768px) { .row select { font-size: 0.75rem; } }")),
    ).toEqual([]);
  });
});
