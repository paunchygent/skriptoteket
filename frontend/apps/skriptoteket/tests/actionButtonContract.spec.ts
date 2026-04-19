/**
 * Shared CTA/action-button CSS contract guard tests.
 *
 * Proves Skriptoteket keeps the CTA/button language promoted into the shared
 * HuleEdu integrated frontend design-system package.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const stylesheetPath = resolve(process.cwd(), "src/assets/main.css");
const stylesheet = readFileSync(stylesheetPath, "utf8");

describe("shared CTA/action-button CSS contract", () => {
  it("keeps reusable CTA and button corners at the approved 4px radius", () => {
    expect(stylesheet).toMatch(/\.btn-primary,\s*\.btn-cta,\s*\.btn-ghost,/);
    expect(stylesheet).toContain("@apply rounded-[4px];");
  });

  it("keeps CTA/button press, shadow, and token roles aligned with the shared contract", () => {
    expect(stylesheet).toContain("@apply active:translate-x-1 active:translate-y-1 active:shadow-none;");
    expect(stylesheet).toContain("@apply bg-navy text-canvas shadow-brutal;");
    expect(stylesheet).toContain("@apply bg-burgundy text-canvas shadow-brutal;");
    expect(stylesheet).toContain("@apply bg-white text-navy shadow-brutal;");
  });
});
