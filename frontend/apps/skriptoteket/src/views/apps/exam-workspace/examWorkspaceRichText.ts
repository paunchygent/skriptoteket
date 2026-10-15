/**
 * Exam workspace rich text values.
 *
 * Domain purpose:
 *   Read the plain text of one paragraph or one rich body, decide whether a
 *   stored body carries any text at all, and build the plain one-paragraph
 *   body a teacher-created question starts with. Adjacent text runs
 *   concatenate as stored (a split word or formula stays one word) and an
 *   atom separates the text around it. Marks never change the text a teacher
 *   reads or the misspelling route sends, so every plain-text consumer reads
 *   through here instead of walking segments itself.
 *
 * Relationships:
 *   - Used by `examWorkspaceDocumentText` (language inference),
 *     `examWorkspaceItemSaveRules` (empty choice and matching entries) and
 *     the editor's choice and matching fields (empty and label text).
 */

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";

/** One paragraph's plain text with collapsed whitespace; gaps and pictures contribute one separator. */
export function paragraphText(paragraph: NativeExamBodyParagraph): string {
  return paragraph.segments
    .map((segment) => (segment.kind === "text" ? segment.text : " "))
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

/** Every paragraph's text of one body, in order, with empty paragraphs dropped. */
export function bodyText(body: NativeExamBodyParagraph[]): string {
  return body.map(paragraphText).filter((text) => text.length > 0).join("\n");
}

/** Whether a body carries no text at all, which the save refuses for a choice or matching entry. */
export function isEmptyBody(body: NativeExamBodyParagraph[]): boolean {
  return body.every((paragraph) =>
    paragraph.segments.every((segment) => segment.kind !== "text" || segment.text.length === 0),
  );
}

/** The plain one-paragraph body a teacher-created question or option starts with. */
export function plainBody(text: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", text, marks: [] }] }];
}
