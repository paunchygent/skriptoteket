/**
 * Exam workspace gap word range.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   The caret inside a word resolves to that word: a maximal run of word
 *   characters touching the caret on either side. A hyphen or an apostrophe
 *   (' or ') with word characters on both sides stays inside the word; a
 *   trailing hyphen does not. Anything else resolves to nothing.
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  gap,
  mountEditor,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { wordRangeAt, wordRangeAtDocPosition } from "./examWorkspaceGapWord";

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

describe("wordRangeAtDocPosition", () => {
  afterEach(() => {
    releaseEditor();
  });

  it("resolves a word split across a bold mark to document positions", async () => {
    const opened = await mountEditor({
      body: [paragraph(text("Huvudstaden är Stock"), text("holm", ["bold"]), text("."))],
    });
    const caret = posIn(opened.editor, "holm", 2);
    const start = posIn(opened.editor, "Stock", 0);
    expect(wordRangeAtDocPosition(opened.editor.state.doc, caret)).toEqual({
      from: start,
      to: start + "Stockholm".length,
    });
  });

  it("resolves only the word after a gap atom", async () => {
    const opened = await mountEditor({
      body: [paragraph(text("Solen är "), gap("gap_001"), text("varm idag"))],
    });
    const caret = posIn(opened.editor, "varm", 1);
    const start = posIn(opened.editor, "varm", 0);
    expect(wordRangeAtDocPosition(opened.editor.state.doc, caret)).toEqual({ from: start, to: start + 4 });
  });

  it("stops at a gap atom on either side of the caret", async () => {
    const opened = await mountEditor({ body: [paragraph(text("ab"), gap("gap_001"), text("cd"))] });
    const beforeGap = posIn(opened.editor, "ab", 2);
    const abStart = posIn(opened.editor, "ab", 0);
    expect(wordRangeAtDocPosition(opened.editor.state.doc, beforeGap)).toEqual({
      from: abStart,
      to: abStart + 2,
    });
    const afterGap = posIn(opened.editor, "cd", 0);
    expect(wordRangeAtDocPosition(opened.editor.state.doc, afterGap)).toEqual({
      from: afterGap,
      to: afterGap + 2,
    });
  });

  it("returns null for a caret between two spaces", async () => {
    const opened = await mountEditor({ body: [paragraph(text("a  b"))] });
    expect(wordRangeAtDocPosition(opened.editor.state.doc, posIn(opened.editor, "a  b", 2))).toBeNull();
  });
});
