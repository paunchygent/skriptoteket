/**
 * Exam workspace whole-document field commands.
 *
 * Domain purpose:
 *   Own the teacher commands that edit one field of the whole exam (the exam
 *   instruction, a part's instruction, the course choice and its Centralt
 *   innehåll ticks) and the printed-total line's fix: clear one level's
 *   printed total.
 *
 * Relationships:
 *   - Every command is one `editDocument` call, the open document's single
 *     edit path (`useExamWorkspaceDocument`), so each is one undo step and
 *     refused while the copy is busy.
 *   - Totals arithmetic lives in `examWorkspaceTotals`.
 */

import type {
  ExamCourseChoice,
  NativeExamDocument,
  NativeExamHeader,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { applyCourseChange } from "./examWorkspaceCourseTags";
import { withoutExamPrintedTotal, withoutPartPrintedTotal } from "./examWorkspaceTotals";
import { withWritingLinesForAllFreeText } from "./examWorkspaceWritingLines";

/** The open document's one edit path for the whole copy. */
export type EditExamWorkspaceDocument = (
  edit: (document: NativeExamDocument) => NativeExamDocument,
  selectId?: string | null,
  structural?: boolean,
) => boolean;

export function useExamWorkspaceDocumentFields({
  editDocument,
  courseKey,
}: {
  editDocument: EditExamWorkspaceDocument;
  /** The working copy's course key; choosing it again makes no edit. */
  courseKey: () => string | null;
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

  /**
   * The exam's course. Choosing it drops the ticks the new course does not
   * own (all of them when cleared), so the stored copy needs no normalising;
   * choosing the course already set makes no edit.
   */
  function setCourse(course: ExamCourseChoice | null): void {
    if ((course?.key ?? null) === courseKey()) {
      return;
    }
    editDocument((document) => applyCourseChange(document, course));
  }

  /** Clear one level's printed total (the exam's when `parentId` is null, else that part's); one undo step. */
  function clearPrintedTotal(parentId: string | null): void {
    editDocument((document) =>
      parentId === null ? withoutExamPrintedTotal(document) : withoutPartPrintedTotal(document, parentId),
    );
  }

  /** Copy one writing-line count to every free-text question; one undo step. */
  function applyWritingLinesToAllFreeText(lines: number): void {
    editDocument((document) => withWritingLinesForAllFreeText(document, lines));
  }

  return {
    applyWritingLinesToAllFreeText,
    clearPrintedTotal,
    setCourse,
    setExamInstructions,
    setParentInstruction,
    setTags,
  };
}
