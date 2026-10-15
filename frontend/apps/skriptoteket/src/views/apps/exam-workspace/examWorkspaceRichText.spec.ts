/**
 * Exam workspace rich text values.
 *
 * Expected behavior:
 *   A paragraph's plain text is the stored text itself: adjacent text runs
 *   concatenate without invented whitespace, so a split word or formula
 *   stays one word (`H` + subscript `2` + `O` reads `H2O`), while a gap or
 *   picture separates the text around it so the words do not fuse.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import { paragraphText } from "./examWorkspaceRichText";

describe("examWorkspaceRichText paragraphText", () => {
  it("concatenates adjacent text runs without invented whitespace", () => {
    const paragraph: NativeExamBodyParagraph = {
      heading_level: null,
      segments: [
        { kind: "text", text: "H", marks: [] },
        { kind: "text", text: "2", marks: ["subscript"] },
        { kind: "text", text: "O", marks: [] },
        { kind: "text", text: "4", marks: ["subscript"] },
      ],
    };

    expect(paragraphText(paragraph)).toBe("H2O4");
  });

  it("keeps one separator where a gap or picture interrupts the text", () => {
    const paragraph: NativeExamBodyParagraph = {
      heading_level: null,
      segments: [
        { kind: "text", text: "Vatten", marks: [] },
        { gap_id: "gap_001", kind: "gap" },
        { kind: "text", text: "kokar", marks: [] },
        { asset_id: "asset_001", kind: "asset" },
        { kind: "text", text: "vid 100 grader.", marks: [] },
      ],
    };

    expect(paragraphText(paragraph)).toBe("Vatten kokar vid 100 grader.");
  });
});
