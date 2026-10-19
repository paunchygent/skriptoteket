/**
 * Teacher-keyed gap misspellings in the pure item transitions.
 *
 * Expected behavior:
 *   A produced misspelling appends to the gap's automatic values exactly once:
 *   an existing automatic value, a gold answer of the question and a spelling
 *   the teacher suppressed are all dropped under the server's spelling policy
 *   (collapsed whitespace, folded case), while the stored spelling keeps its
 *   display form. Removing an automatic value also records the suppression on
 *   the gap, so neither a later reply nor a later accepted-values edit brings
 *   it back.
 */

import { describe, expect, it } from "vitest";

import {
  itemAcceptedAnswers,
  withAutomaticValues,
  withGapValues,
  withoutAutomaticValue,
} from "./examWorkspaceGapEdits";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";

function keyedItem() {
  return gapItem(
    "teacher_authored",
    [
      ["gap_001", ["Stockholm", "Sthlm"]],
      ["gap_002", ["Oslo"]],
    ],
    null,
  );
}

describe("itemAcceptedAnswers", () => {
  it("lists every keyed answer once, in gap order", () => {
    const item = withGapValues(keyedItem(), "gap_002", ["Oslo", "Stockholm"]);

    expect(itemAcceptedAnswers(item)).toEqual(["Stockholm", "Sthlm", "Oslo"]);
  });
});

describe("withAutomaticValues", () => {
  it("appends produced spellings after the existing ones and keeps the untouched gap", () => {
    const source = keyedItem();
    const result = withAutomaticValues(source, "gap_001", ["Stockhom", "Stokholm"]);

    expect(result.gaps[0]?.automatic_values).toEqual(["Stockhom", "Stokholm"]);
    expect(result.gaps[1]).toBe(source.gaps[1]);
    expect(result.answer_key).toEqual(source.answer_key);
  });

  it("drops duplicates, gold answers and suppressed values under the spelling policy", () => {
    const source = withAutomaticValues(keyedItem(), "gap_001", ["Stockhom"]);
    const suppressed = withoutAutomaticValue(source, "gap_001", "Stockhom");

    const result = withAutomaticValues(suppressed, "gap_001", [
      "stockhom",
      "Stockholm",
      "Sthlm",
      "oslo",
    ]);

    expect(result).toBe(suppressed);
  });

  it("keeps the producer's order and each spelling's display form", () => {
    const result = withAutomaticValues(keyedItem(), "gap_001", ["Götebprg", "götebprg"]);

    expect(result.gaps[0]?.automatic_values).toEqual(["Götebprg"]);
  });

  it("returns the item unchanged without produced values or for an unknown gap", () => {
    const source = keyedItem();

    expect(withAutomaticValues(source, "gap_001", [])).toBe(source);
    expect(withAutomaticValues(source, "gap_999", ["Stockhom"])).toBe(source);
  });
});

describe("withoutAutomaticValue", () => {
  it("removes the value and records the suppression", () => {
    const source = withAutomaticValues(keyedItem(), "gap_001", ["Stockhom", "Stokholm"]);

    const result = withoutAutomaticValue(source, "gap_001", "Stokholm");

    expect(result.gaps[0]?.automatic_values).toEqual(["Stockhom"]);
    expect(result.gaps[0]?.excluded_automatic_values).toEqual(["Stokholm"]);
    expect(result.gaps[1]).toBe(source.gaps[1]);
  });

  it("matches a stored spelling under the spelling policy and stores the display form", () => {
    const source = withAutomaticValues(keyedItem(), "gap_001", ["Stockhom"]);

    const result = withoutAutomaticValue(source, "gap_001", "  stockhom ");

    expect(result.gaps[0]?.automatic_values).toEqual([]);
    expect(result.gaps[0]?.excluded_automatic_values).toEqual(["  stockhom "]);
  });

  it("leaves an unknown value and an unknown gap untouched", () => {
    const source = withAutomaticValues(keyedItem(), "gap_001", ["Stockhom"]);

    expect(withoutAutomaticValue(source, "gap_001", "missing")).toBe(source);
    expect(withoutAutomaticValue(source, "gap_999", "Stockhom")).toBe(source);
  });

  it("keeps the suppression through a later key edit and never re-adds the value", () => {
    const removed = withoutAutomaticValue(
      withAutomaticValues(keyedItem(), "gap_001", ["Stockhom"]),
      "gap_001",
      "Stockhom",
    );

    const rekeyed = withGapValues(removed, "gap_001", ["Stockholm", "Sthlm", "Göteborg"]);
    expect(rekeyed.gaps[0]?.excluded_automatic_values).toEqual(["Stockhom"]);

    const later = withAutomaticValues(rekeyed, "gap_001", ["Stockhom"]);
    expect(later.gaps[0]?.automatic_values).toEqual([]);
  });
});
