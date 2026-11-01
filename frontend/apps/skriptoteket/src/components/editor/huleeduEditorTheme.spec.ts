/**
 * huleeduEditorTheme colour contract (TASK-SKRIPT-42-01-02).
 *
 * Expected behavior:
 *   Every colour-valued property in `huleeduEditorThemeSpec` reads a
 *   `--huleedu-editor-*` token and every colour in `huleeduHighlightStyle.specs`
 *   reads a `--huleedu-syntax-*` token, so a `data-theme` change repaints both
 *   CodeMirror editors through CSS with no reload.
 *
 * Relationships:
 *   - The assertions walk the exported objects, so they hold whichever
 *     selectors and properties the module declares.
 */

import { describe, expect, it } from "vitest";

import { huleeduEditorThemeSpec, huleeduHighlightStyle } from "./huleeduEditorTheme";

const COLOUR_PROPERTY = /^(color|accentColor|caretColor|columnRuleColor|background|backgroundColor|border(Color|TopColor|RightColor|BottomColor|LeftColor)|outlineColor|textDecorationColor|fill|stroke)$/;
const EDITOR_TOKEN = /^var\(--huleedu-editor-[a-z-]+\)$/;
const SYNTAX_TOKEN = /^var\(--huleedu-syntax-[a-z-]+\)$/;

interface ColourRule {
  selector: string;
  property: string;
  value: unknown;
}

function collectColourRules(spec: Record<string, unknown>, selector = ""): ColourRule[] {
  const rules: ColourRule[] = [];
  for (const [key, value] of Object.entries(spec)) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      rules.push(...collectColourRules(value as Record<string, unknown>, key));
    } else if (COLOUR_PROPERTY.test(key)) {
      rules.push({ selector, property: key, value });
    }
  }
  return rules;
}

describe("huleeduEditorThemeSpec", () => {
  it("reads every colour from a --huleedu-editor-* token", () => {
    const rules = collectColourRules(huleeduEditorThemeSpec);
    expect(rules.length).toBeGreaterThan(0);
    for (const rule of rules) {
      expect(
        rule.value,
        `${rule.selector} ${rule.property} must read a --huleedu-editor-* token`,
      ).toMatch(EDITOR_TOKEN);
    }
  });

  it("covers the editor background, gutter, gutter text, cursor, selection and active line", () => {
    const tokens = new Set(
      collectColourRules(huleeduEditorThemeSpec).map((rule) => String(rule.value)),
    );
    for (const token of ["bg", "gutter-bg", "gutter-text", "cursor", "selection", "active-line"]) {
      expect(tokens.has(`var(--huleedu-editor-${token})`), `--huleedu-editor-${token}`).toBe(true);
    }
  });
});

describe("huleeduHighlightStyle", () => {
  it("reads every colour from a --huleedu-syntax-* token", () => {
    expect(huleeduHighlightStyle.specs.length).toBeGreaterThan(0);
    for (const spec of huleeduHighlightStyle.specs) {
      for (const [property, value] of Object.entries(spec)) {
        if (property === "tag" || !COLOUR_PROPERTY.test(property)) continue;
        expect(value, `${property} must read a --huleedu-syntax-* token`).toMatch(SYNTAX_TOKEN);
      }
    }
  });

  it("covers the comment, function, keyword, number and string tokens", () => {
    const tokens = new Set(
      huleeduHighlightStyle.specs.flatMap((spec) =>
        Object.entries(spec)
          .filter(([property]) => COLOUR_PROPERTY.test(property))
          .map(([, value]) => String(value)),
      ),
    );
    for (const token of ["comment", "function", "keyword", "number", "string"]) {
      expect(tokens.has(`var(--huleedu-syntax-${token})`), `--huleedu-syntax-${token}`).toBe(true);
    }
  });
});
