/**
 * Exam workspace gap word range.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   The caret inside a word resolves to that word: a maximal run of word
 *   characters touching the caret on either side. A hyphen or an apostrophe
 *   (' or ') with word characters on both sides stays inside the word; a
 *   trailing hyphen does not. Anything else resolves to nothing.
 */

import { describe, expect, it } from "vitest";

import { wordRangeAt } from "./examWorkspaceGapWord";

describe("wordRangeAt", () => {
  it("resolves a caret inside a word to the whole word", () => {
    expect(wordRangeAt("Paris", 2)).toEqual({ from: 0, to: 5 });
  });

  it("resolves a caret at the start of a word to that word", () => {
    expect(wordRangeAt("Paris", 0)).toEqual({ from: 0, to: 5 });
  });

  it("resolves a caret at the end of a word to that word", () => {
    expect(wordRangeAt("Paris.", 5)).toEqual({ from: 0, to: 5 });
  });

  it("returns null for a caret between two spaces", () => {
    expect(wordRangeAt("a  b", 2)).toBeNull();
  });

  it("keeps a hyphen with word characters on both sides inside one word", () => {
    expect(wordRangeAt("Stockholms-läns", 11)).toEqual({ from: 0, to: 15 });
  });

  it("keeps an apostrophe with word characters on both sides inside one word", () => {
    expect(wordRangeAt("don't", 2)).toEqual({ from: 0, to: 5 });
  });

  it("excludes a trailing hyphen from the word", () => {
    expect(wordRangeAt("ord- ", 3)).toEqual({ from: 0, to: 3 });
  });

  it("resolves å, ä, ö and digits as word characters", () => {
    expect(wordRangeAt("åäö123", 3)).toEqual({ from: 0, to: 6 });
  });

  it("keeps a combining mark inside the word", () => {
    expect(wordRangeAt("école", 1)).toEqual({ from: 0, to: 6 });
  });

  it("resolves a caret next to punctuation at end-of-word offset to the word", () => {
    expect(wordRangeAt("Paris.", 5)).toEqual({ from: 0, to: 5 });
    expect(wordRangeAt("Paris.", 6)).toBeNull();
  });
});
