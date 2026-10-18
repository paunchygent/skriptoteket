/**
 * Exam workspace question-text export readiness.
 *
 * Expected behavior:
 *   A question whose text prints nothing reports `empty_question_text`, the
 *   same rule as the server's `is_empty_body` (no gap, no picture, every text
 *   blank); a gap or dropdown question without a gap reports `no_gaps`. Both
 *   come right after the unbuilt question, empty text first.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";

const paragraph = (...segments: NativeExamBodyParagraph["segments"]): NativeExamBodyParagraph => ({
  heading_level: null,
  segments,
});
const text = (value: string): NativeExamBodyParagraph["segments"][number] => ({
  kind: "text",
  marks: [],
  text: value,
});
const gapSegment = { gap_id: "gap_001", kind: "gap" } as const;
const pictureSegment = { asset_id: "asset_1", kind: "asset" } as const;

function gapItem(kind: "gap_fill" | "inline_choice", overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return buildChoiceItem({
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    choices: [],
    kind,
    ...overrides,
  });
}

describe("question text readiness", () => {
  it.each([
    ["no paragraph", []],
    ["one empty paragraph", [paragraph()]],
    ["a blank text run", [paragraph(text("  \n "))]],
    ["blank paragraphs only", [paragraph(text(" ")), paragraph(text("\t"))]],
  ])("blocks a question whose body is %s", (_name, body) => {
    expect(examWorkspaceItemReadiness(buildChoiceItem({ body }))).toEqual(["empty_question_text"]);
  });

  it.each([
    ["text", [paragraph(text(" a "))]],
    ["only a picture", [paragraph(pictureSegment)]],
    ["only a gap", [paragraph(gapSegment)]],
    ["a blank run before a picture", [paragraph(text(" "), pictureSegment)]],
  ])("does not block a question whose body holds %s", (_name, body) => {
    expect(examWorkspaceItemReadiness(buildChoiceItem({ body }))).not.toContain("empty_question_text");
  });

  it.each(["gap_fill", "inline_choice"] as const)("blocks %s without a gap", (kind) => {
    const item = gapItem(kind, { body: [paragraph(text("Fyll i."))], gaps: [] });

    expect(examWorkspaceItemReadiness(item)).toContain("no_gaps");
  });

  it("never reports no_gaps for a kind that has no gaps", () => {
    for (const kind of ["free_text", "single_choice", "multiple_response", "ordering", "matching"] as const) {
      expect(examWorkspaceItemReadiness(buildChoiceItem({ kind, gaps: [] }))).not.toContain("no_gaps");
    }
  });

  it("names the empty text before the missing gaps", () => {
    const item = gapItem("gap_fill", { body: [], gaps: [] });

    expect(examWorkspaceItemReadiness(item).slice(0, 2)).toEqual(["empty_question_text", "no_gaps"]);
  });

  it("keeps the unbuilt question ahead of the empty text and the missing gaps", () => {
    const item = gapItem("gap_fill", {
      body: [],
      gaps: [],
      review: { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" },
    });

    expect(examWorkspaceItemReadiness(item).slice(0, 3)).toEqual([
      "unbuilt_question",
      "empty_question_text",
      "no_gaps",
    ]);
  });
});
