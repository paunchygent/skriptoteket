/**
 * Exam workspace whole-document field commands.
 *
 * Domain purpose:
 *   Own the teacher commands that edit one field of the whole exam (the exam
 *   instruction, a part's instruction, the Centralt innehåll ticks) and the
 *   printed-total note's answers: no keeps the printed numbers and dismisses
 *   the note, yes uses the questions' sums over the printed totals.
 *
 * Relationships:
 *   - Every command is one `editDocument` call, the open document's single
 *     edit path (`useExamWorkspaceDocument`), so each is one undo step and
 *     refused while the copy is busy.
 *   - Totals arithmetic lives in `examWorkspaceTotals`.
 */

import type { NativeExamDocument, NativeExamHeader, NativeExamParent } from "../../../api/examWorkspace";
import { withoutPrintedTotals } from "./examWorkspaceTotals";
import { withWritingLinesForAllFreeText } from "./examWorkspaceWritingLines";

/** The open document's one edit path for the whole copy. */
export type EditExamWorkspaceDocument = (
  edit: (document: NativeExamDocument) => NativeExamDocument,
  selectId?: string | null,
  structural?: boolean,
) => boolean;

export function useExamWorkspaceDocumentFields({
  editDocument,
}: {
  editDocument: EditExamWorkspaceDocument;
}) {
  /** The instruction text above an instruction's deluppgifter, typed like a question's text. */
  function setParentInstruction(
    parentId: string,
    instruction: NativeExamParent["instruction"],
    structural: boolean,
  ): void {
    editDocument(
      (document) => ({
        ...document,
        parents: document.parents.map((parent) =>
          parent.parent_id === parentId ? { ...parent, instruction } : parent,
        ),
      }),
      null,
      structural,
    );
  }

  /** The exam instruction printed before the first question, typed like a question's text; emptied it is `[]`. */
  function setExamInstructions(instructions: NativeExamDocument["instructions"], structural: boolean): void {
    editDocument((document) => ({ ...document, instructions }), null, structural);
  }

  /** The exam's Centralt innehåll ticks; each tick is its own undo step. */
  function setTags(tags: NativeExamHeader["tags"]): void {
    editDocument((document) => ({ ...document, header: { ...document.header, tags } }));
  }

  /** Keep the printed numbers and dismiss the points note; one undo step. */
  function dismissPrintedTotal(): void {
    editDocument((document) => ({
      ...document,
      header: { ...document.header, printed_total_dismissed: true },
    }));
  }

  /** Use the questions' sums over the exam and every part's printed total; one undo step. */
  function useComputedPoints(): void {
    editDocument(withoutPrintedTotals);
  }

  /** Copy one writing-line count to every free-text question; one undo step. */
  function applyWritingLinesToAllFreeText(lines: number): void {
    editDocument((document) => withWritingLinesForAllFreeText(document, lines));
  }

  return {
    applyWritingLinesToAllFreeText,
    dismissPrintedTotal,
    setExamInstructions,
    setParentInstruction,
    setTags,
    useComputedPoints,
  };
}
