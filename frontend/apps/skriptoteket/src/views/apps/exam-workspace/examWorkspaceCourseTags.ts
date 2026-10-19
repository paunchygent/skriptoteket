/**
 * Exam workspace course-tag rule.
 *
 * Domain purpose:
 *   Centralt innehåll ticks are exam metadata that categorise the exam, not
 *   grading criteria: they stay apart from the per-question
 *   Bedömningskriterier. A tick belongs to the course chosen for the exam,
 *   named by the `<course_key>:` id prefix. Choosing another course keeps
 *   only the ticks the new course owns; clearing the course keeps none. The
 *   same rule runs on the server (NativeExamHeader), so the working copy
 *   applies it at once instead of storing a copy the server normalises.
 *
 * Relationships:
 *   - Pure: the course commands in `useExamWorkspaceDocumentFields` apply it
 *     through the document's one edit path, so each course change is one
 *     undo step.
 */

import type { ExamCourseChoice, NativeExamDocument } from "../../../api/examWorkspace";

/**
 * Apply a course change to the working copy, dropping the ticks the new
 * course does not own. Returns the document itself when the course key is
 * unchanged, so the caller makes no edit.
 */
export function applyCourseChange(
  document: NativeExamDocument,
  course: ExamCourseChoice | null,
): NativeExamDocument {
  const nextKey = course?.key ?? null;
  if ((document.header.course?.key ?? null) === nextKey) {
    return document;
  }
  const tags =
    nextKey === null
      ? []
      : document.header.tags.filter((item) => item.id.startsWith(`${nextKey}:`));
  return { ...document, header: { ...document.header, course, tags } };
}
