/**
 * Exam workspace document text.
 *
 * Domain purpose:
 *   Flatten one exam document's readable text in reading order: the title,
 *   the shared instructions, and every question's printed label, facit, body,
 *   choices and match entries. The misspelling route reads the text to infer
 *   the exam's language, so key values and produced spellings stay out of it.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceGapKeying`, which sends it with each keying
 *     request.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";

/** One paragraph's plain text: text segments in order, gaps and pictures named by nothing. */
function paragraphText(paragraph: NativeExamBodyParagraph): string {
  return paragraph.segments
    .map((segment) => (segment.kind === "text" ? segment.text : ""))
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function paragraphsText(paragraphs: NativeExamBodyParagraph[]): string[] {
  return paragraphs.map(paragraphText).filter((text) => text.length > 0);
}

/** Every readable text of the document, in reading order, without its key values. */
export function examWorkspaceDocumentText(document: NativeExamDocument): string {
  const lines: string[] = [document.title.trim()];
  lines.push(...paragraphsText(document.instructions));
  for (const parent of document.parents) {
    lines.push(...paragraphsText(parent.instruction));
  }
  for (const item of document.items) {
    for (const text of [item.printed_label, item.facit_text]) {
      if (text !== null && text.trim().length > 0) {
        lines.push(text.trim());
      }
    }
    lines.push(...paragraphsText(item.body));
    lines.push(...item.choices.map((choice) => choice.text.trim()));
    lines.push(...item.match_left.map((entry) => entry.text.trim()));
    lines.push(...item.match_right.map((entry) => entry.text.trim()));
  }
  return lines.filter((line) => line.length > 0).join("\n");
}
