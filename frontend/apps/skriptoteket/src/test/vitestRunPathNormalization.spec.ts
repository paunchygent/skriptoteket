/**
 * @fileoverview Locks down SPA Vitest path normalization so the wrapper accepts
 * repo-root and app-local test targets without cwd-sensitive drift.
 */

import { describe, expect, it } from "vitest";

import {
  collectVitestTargets,
  normalizeVitestArgs,
  normalizeVitestPathArg,
} from "../../scripts/vitest-run.mjs";

describe("vitest-run path normalization", () => {
  it("normalizes repo-root explicit test paths to app-local paths", () => {
    expect(
      normalizeVitestPathArg(
        "frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts",
      ),
    ).toBe("src/views/apps/ClassroomPlannerEntryView.spec.ts");
  });

  it("preserves app-local test paths", () => {
    expect(normalizeVitestPathArg("src/views/apps/ClassroomPlannerEntryView.spec.ts")).toBe(
      "src/views/apps/ClassroomPlannerEntryView.spec.ts",
    );
  });

  it("preserves Vitest line selectors while normalizing paths", () => {
    expect(
      normalizeVitestPathArg(
        "frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts:42",
      ),
    ).toBe("src/views/apps/ClassroomPlannerEntryView.spec.ts:42");
  });

  it("normalizes repo-root glob targets before computing include patterns", () => {
    expect(
      collectVitestTargets(
        normalizeVitestArgs(["frontend/apps/skriptoteket/src/views/apps/*.spec.ts"]),
      ),
    ).toEqual(["src/views/apps/*.spec.ts"]);
  });

  it("does not treat helper files with spec-like names as runnable tests", () => {
    expect(
      collectVitestTargets(
        normalizeVitestArgs([
          "src/components/apps/flunk-out-frenzy/game/table/compilePinballTable.spec-support.ts",
        ]),
      ),
    ).toEqual([]);
  });
});
