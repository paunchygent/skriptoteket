/**
 * Client gap placement rule against the shared case table (TASK-SKRIPT-39-05-15 D9).
 *
 * Expected behavior:
 *   The client's `withGapTextShape` follows the same placement rule as the
 *   server retype to Lucktext: the gap lands at the end of the last question
 *   paragraph (trailing empty paragraphs drop; a space separates text without
 *   trailing whitespace; an empty question gives the gap paragraph then an
 *   empty paragraph), so Lucktext opens as Lucktext with the gap tools, not
 *   as Kort svar. Every case comes from the one shared table at
 *   `tests/fixtures/exam_workspace/gap_text_placement_cases.json`, asserted
 *   here and by the pytest suite, so the client and the server cannot drift.
 */

import { describe, expect, it } from "vitest";

import placementTable from "../../../../../../../tests/fixtures/exam_workspace/gap_text_placement_cases.json";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { withGapTextShape } from "./examWorkspaceShortAnswer";

type TextMark = Extract<NativeExamBodySegment, { kind: "text" }>["marks"][number];

type PlacementCase = {
  name: string;
  question: NativeExamBodyParagraph[];
  expected: NativeExamBodyParagraph[];
};

type PlacementTable = {
  gap_id: string;
  cases: PlacementCase[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMark(value: unknown): value is TextMark {
  return (
    value === "bold" ||
    value === "italic" ||
    value === "underline" ||
    value === "superscript" ||
    value === "subscript"
  );
}

function isSegment(value: unknown): value is NativeExamBodySegment {
  if (!isRecord(value)) {
    return false;
  }
  if (value.kind === "text") {
    return (
      typeof value.text === "string" &&
      Array.isArray(value.marks) &&
      value.marks.every(isMark) &&
      (value.kept_gap_id === undefined ||
        value.kept_gap_id === null ||
        typeof value.kept_gap_id === "string")
    );
  }
  if (value.kind === "gap") {
    return typeof value.gap_id === "string";
  }
  if (value.kind === "asset") {
    return typeof value.asset_id === "string";
  }
  return false;
}

function isParagraph(value: unknown): value is NativeExamBodyParagraph {
  if (!isRecord(value)) {
    return false;
  }
  const heading = value.heading_level;
  const headingOk = heading === null || heading === 1 || heading === 2 || heading === 3;
  return headingOk && Array.isArray(value.segments) && value.segments.every(isSegment);
}

function isPlacementCase(value: unknown): value is PlacementCase {
  return (
    isRecord(value) &&
    typeof value.name === "string" &&
    Array.isArray(value.question) &&
    value.question.every(isParagraph) &&
    Array.isArray(value.expected) &&
    value.expected.every(isParagraph)
  );
}

function isPlacementTable(value: unknown): value is PlacementTable {
  return (
    isRecord(value) &&
    typeof value.gap_id === "string" &&
    Array.isArray(value.cases) &&
    value.cases.every(isPlacementCase)
  );
}

const parsed: unknown = placementTable;

if (!isPlacementTable(parsed)) {
  throw new Error("invalid gap placement case table at gap_text_placement_cases.json");
}

/** A Kort svar item whose question is the case input and whose lone gap waits last. */
function kortSvarItem(gapId: string, question: NativeExamBodyParagraph[]): NativeExamItem {
  return {
    ...newTeacherItem("item_001", 1, "gap_fill"),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body: [...question, { heading_level: null, segments: [{ kind: "gap", gap_id: gapId }] }],
    gaps: [buildGap(gapId)],
    kind: "gap_fill",
  };
}

describe("withGapTextShape shared placement cases (D9)", () => {
  for (const placementCase of parsed.cases) {
    it(`places the gap for ${placementCase.name}`, () => {
      const item = kortSvarItem(parsed.gap_id, placementCase.question);

      expect(withGapTextShape(item).body).toEqual(placementCase.expected);
    });
  }
});
