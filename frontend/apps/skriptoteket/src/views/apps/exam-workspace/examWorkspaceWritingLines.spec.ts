/**
 * Writing-area transitions (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   A stepper value is a whole number of lines inside the house range, only a
 *   free-text question carries it, and the apply-to-all transition changes
 *   every free-text question while leaving other kinds and the document itself
 *   untouched when nothing moves. The free-text summary lists only free-text
 *   questions, in document order, with their display labels and counts (null
 *   when a question carries none); a null count differs from every count.
 */

import { describe, expect, it } from "vitest";

import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { examWorkspaceQuestionLabels } from "./examWorkspaceListEntries";
import {
  freeTextWritingLines,
  labelsWithOtherWritingLines,
  MAX_WRITING_LINES,
  MIN_WRITING_LINES,
  withWritingLines,
  withWritingLinesForAllFreeText,
} from "./examWorkspaceWritingLines";

function freeText(sequence: number, lines: number | null) {
  return buildFreeTextItem(sequence, { writing_lines: lines });
}

function choice(sequence: number) {
  return buildFreeTextItem(sequence, { kind: "single_choice", writing_lines: null });
}

describe("withWritingLines", () => {
  it("clamps a stepper value into the house range as a whole number of lines", () => {
    expect(withWritingLines(freeText(1, 8), 0).writing_lines).toBe(MIN_WRITING_LINES);
    expect(withWritingLines(freeText(1, 8), 41).writing_lines).toBe(MAX_WRITING_LINES);
    expect(withWritingLines(freeText(1, 8), 7.6).writing_lines).toBe(8);
  });

  it("leaves an item of another kind untouched", () => {
    const item = choice(1);

    expect(withWritingLines(item, 5)).toBe(item);
  });
});

describe("withWritingLinesForAllFreeText", () => {
  it("sets every free-text item and leaves other kinds identical", () => {
    const first = freeText(1, 8);
    const second = freeText(2, 12);
    const other = choice(3);
    const document = { ...buildParentDocument(), items: [first, second, other] };

    const next = withWritingLinesForAllFreeText(document, 3);

    expect(next.items.map((item) => item.writing_lines)).toEqual([3, 3, null]);
    expect(next.items[2]).toBe(other);
  });

  it("clamps the shared value into the house range", () => {
    const document = { ...buildParentDocument(), items: [freeText(1, 8)] };

    expect(withWritingLinesForAllFreeText(document, 0).items[0]!.writing_lines).toBe(
      MIN_WRITING_LINES,
    );
  });

  it("keeps a free-text item already at the count and returns the same document", () => {
    const item = freeText(1, 3);
    const document = { ...buildParentDocument(), items: [item] };

    const next = withWritingLinesForAllFreeText(document, 3);

    expect(next.items[0]).toBe(item);
    expect(next).toBe(document);
  });
});

describe("freeTextWritingLines", () => {
  it("lists only free-text questions in document order with display labels and counts", () => {
    const document = {
      ...buildParentDocument(),
      items: [freeText(1, 8), choice(2), freeText(3, null), freeText(4, 12)],
    };

    const summary = freeTextWritingLines(document, examWorkspaceQuestionLabels(document));

    expect(summary.map((entry) => entry.itemId)).toEqual(["item_001", "item_003", "item_004"]);
    expect(summary.map((entry) => entry.lines)).toEqual([8, null, 12]);
    expect(summary.map((entry) => entry.label)).toEqual(["1a", "1c", "2"]);
  });

  it("falls back to the item id when a question has no display label", () => {
    const document = { ...buildParentDocument(), items: [freeText(1, 8)] };

    expect(freeTextWritingLines(document, new Map())).toEqual([
      { itemId: "item_001", label: "item_001", lines: 8 },
    ]);
  });
});

describe("labelsWithOtherWritingLines", () => {
  const summary = [
    { itemId: "a", label: "1a", lines: 4 },
    { itemId: "b", label: "1b", lines: 8 },
    { itemId: "c", label: "2", lines: null },
    { itemId: "d", label: "3", lines: 8 },
  ];

  it("names the questions whose count differs, a missing count included, in order", () => {
    expect(labelsWithOtherWritingLines(summary, 8)).toEqual(["1a", "2"]);
  });

  it("names none when every question has the count", () => {
    expect(labelsWithOtherWritingLines([summary[1]!, summary[3]!], 8)).toEqual([]);
  });
});
