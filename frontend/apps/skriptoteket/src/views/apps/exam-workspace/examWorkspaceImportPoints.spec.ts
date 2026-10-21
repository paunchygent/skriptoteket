/**
 * The import-time points check behind the question list's import line
 * (TASK-SKRIPT-40-04-23).
 *
 * Expected behavior:
 *   A question differs when the source printed a value for it
 *   (`source_points` non-null) and its points are missing or another number
 *   beyond binary-float error. `examWorkspaceImportPointsItemIds` names the
 *   differing questions in list order, parts' questions included, whatever
 *   the printed exam and part totals say. `examWorkspaceNextImportPointsTarget`
 *   steps from the selected question to the next differing one and wraps to
 *   the first. The line reads "{N} frågor avviker från provtexten", singular
 *   "1 fråga avviker från provtexten".
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import {
  examWorkspaceImportPointsItemIds,
  examWorkspaceImportPointsText,
  examWorkspaceNextImportPointsTarget,
} from "./examWorkspaceImportPoints";
import { examWorkspaceSourcePointsDiffer } from "./examWorkspaceTotals";

function question(itemId: string, points: number | null, source: number | null): NativeExamItem {
  return { ...newTeacherItem(itemId, 1, "free_text"), points, source_points: source };
}

describe("examWorkspaceSourcePointsDiffer", () => {
  it("counts another number and missing points against a printed value", () => {
    expect(examWorkspaceSourcePointsDiffer(question("a", 5, 4))).toBe(true);
    expect(examWorkspaceSourcePointsDiffer(question("a", null, 4))).toBe(true);
  });

  it("never counts a question whose source printed nothing, or the same value", () => {
    expect(examWorkspaceSourcePointsDiffer(question("a", 5, null))).toBe(false);
    expect(examWorkspaceSourcePointsDiffer(question("a", null, null))).toBe(false);
    expect(examWorkspaceSourcePointsDiffer(question("a", 4, 4))).toBe(false);
    expect(examWorkspaceSourcePointsDiffer(question("a", 0.1 + 0.2, 0.3))).toBe(false);
  });
});

describe("examWorkspaceImportPointsItemIds", () => {
  it("names the differing questions in list order, not document item order", () => {
    const items = [question("q1", 5, 4), question("q2", 3, 3), question("q3", 2, 1)];
    const order = ["q3", "q2", "q1"];

    expect(examWorkspaceImportPointsItemIds(order, items)).toEqual(["q3", "q1"]);
  });

  it("is empty when no question differs", () => {
    const items = [question("q1", 4, 4), question("q2", 3, null)];

    expect(examWorkspaceImportPointsItemIds(["q1", "q2"], items)).toEqual([]);
  });

  it("skips a listed id that names no question", () => {
    expect(examWorkspaceImportPointsItemIds(["part-1", "q1"], [question("q1", 5, 4)])).toEqual(["q1"]);
  });
});

describe("examWorkspaceNextImportPointsTarget", () => {
  const ids = ["q1", "q3", "q5"];

  it("starts at the first differing question when nothing or another row is selected", () => {
    expect(examWorkspaceNextImportPointsTarget(ids, null)).toBe("q1");
    expect(examWorkspaceNextImportPointsTarget(ids, "q2")).toBe("q1");
  });

  it("steps to the next differing question and wraps to the first", () => {
    expect(examWorkspaceNextImportPointsTarget(ids, "q1")).toBe("q3");
    expect(examWorkspaceNextImportPointsTarget(ids, "q3")).toBe("q5");
    expect(examWorkspaceNextImportPointsTarget(ids, "q5")).toBe("q1");
  });

  it("has no target without a differing question", () => {
    expect(examWorkspaceNextImportPointsTarget([], "q1")).toBeNull();
  });
});

describe("examWorkspaceImportPointsText", () => {
  it("reads in the singular for one question and the plural otherwise", () => {
    expect(examWorkspaceImportPointsText(1)).toBe("1 fråga avviker från provtexten");
    expect(examWorkspaceImportPointsText(3)).toBe("3 frågor avviker från provtexten");
  });
});
