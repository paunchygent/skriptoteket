/**
 * Writing-area transitions (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   A stepper value is a whole number of lines inside the house range, only a
 *   free-text question carries it, and the apply-to-all transition changes
 *   every free-text question while leaving other kinds and the document itself
 *   untouched when nothing moves.
 */

import { describe, expect, it } from "vitest";

import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
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
