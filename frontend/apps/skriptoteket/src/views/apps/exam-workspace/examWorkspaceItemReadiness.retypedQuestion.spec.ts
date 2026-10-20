/**
 * Exam workspace readiness for a retyped unconverted question (TASK-SKRIPT-39-05-15 D3).
 *
 * Expected behavior:
 *   A review_required item with parse_origin teacher_created (a type chosen
 *   on an unconverted question) reports the new reason
 *   "unreviewed_retyped_question" and no longer reports "unbuilt_question".
 *   A reviewed teacher_created item reports nothing; review_required with any
 *   other origin (llm_parsed, deterministic, source_fallback) never reports
 *   the new reason.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";

function retyped(overrides: Partial<NativeExamItem["review"]> = {}): NativeExamItem {
  return {
    ...gapItem("teacher_authored", [["gap_001", ["Paris"]]], null),
    review: { confidence: null, parse_origin: "teacher_created", reasons: [], state: "review_required", ...overrides },
  };
}

describe("examWorkspaceItemReadiness for a retyped unconverted question", () => {
  it("lists unreviewed_retyped_question and not unbuilt_question while review is required", () => {
    expect(examWorkspaceItemReadiness(retyped())).toEqual(["unreviewed_retyped_question"]);
  });

  it("lists nothing once the retyped question is marked reviewed", () => {
    expect(examWorkspaceItemReadiness(retyped({ state: "review_complete" }))).toEqual([]);
  });

  it("never lists the new reason for review_required with another origin", () => {
    for (const parse_origin of ["llm_parsed", "deterministic", "source_fallback"] as const) {
      const item = buildChoiceItem({
        review: { confidence: null, parse_origin, reasons: [], state: "review_required" },
      });
      expect(examWorkspaceItemReadiness(item)).not.toContain("unreviewed_retyped_question");
    }
  });

  it("keeps the unbuilt rule for a source_fallback item without the new reason", () => {
    const item = buildChoiceItem({
      review: { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" },
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["unbuilt_question"]);
  });
});
