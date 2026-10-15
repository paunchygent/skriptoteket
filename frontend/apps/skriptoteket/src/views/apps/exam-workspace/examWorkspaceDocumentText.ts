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
 *   - Reads its paragraph flattening from `examWorkspaceRichText`.
 */

import type { NativeExamBodyParagraph, NativeExamDocument } from "../../../api/examWorkspace";
import { paragraphText } from "./examWorkspaceRichText";

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
    lines.push(...item.choices.flatMap((choice) => paragraphsText(choice.body)));
    lines.push(...item.match_left.flatMap((entry) => paragraphsText(entry.body)));
    lines.push(...item.match_right.flatMap((entry) => paragraphsText(entry.body)));
  }
  return lines.filter((line) => line.length > 0).join("\n");
}
