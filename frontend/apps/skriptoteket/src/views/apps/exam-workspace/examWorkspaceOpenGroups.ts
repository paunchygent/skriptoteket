/**
 * Exam workspace Öppna list groups.
 *
 * Domain purpose:
 *   The teacher's saved exams as Öppna lists them. "Per kurs" groups them by
 *   course: the teacher's own courses first in the order the profile keeps
 *   them, then every other course by its Swedish name, then "Utan kurs".
 *   "Senaste" is one list. Inside every group the newest save comes first.
 *
 * Relationships:
 *   - Read by `ExamWorkspaceOpenDrawer`; course names come from the course
 *     catalog, and an unknown course keeps its key as its name.
 */

import type { ExamListOrdering, ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";

export type ExamWorkspaceOpenGroup = {
  /** Null for the single "Senaste" list. */
  heading: string | null;
  courseKey: string | null;
  documents: ExamWorkspaceDocumentSummary[];
};

const NO_COURSE = "Utan kurs";

function newestFirst(documents: readonly ExamWorkspaceDocumentSummary[]): ExamWorkspaceDocumentSummary[] {
  return [...documents].sort((left, right) => right.saved_at.localeCompare(left.saved_at));
}

export function examWorkspaceOpenGroups(
  documents: readonly ExamWorkspaceDocumentSummary[],
  ordering: ExamListOrdering,
  registeredCourseKeys: readonly string[],
  courseName: (key: string) => string | null,
): ExamWorkspaceOpenGroup[] {
  const sorted = newestFirst(documents);
  if (ordering !== "course") {
    return sorted.length > 0 ? [{ heading: null, courseKey: null, documents: sorted }] : [];
  }
  const nameOf = (key: string) => courseName(key) ?? key;
  const registered = new Map(registeredCourseKeys.map((key, index) => [key, index]));
  const keys = [...new Set(sorted.flatMap((entry) => (entry.course_key ? [entry.course_key] : [])))].sort(
    (left, right) =>
      (registered.get(left) ?? registered.size) - (registered.get(right) ?? registered.size) ||
      nameOf(left).localeCompare(nameOf(right), "sv"),
  );
  const groups: ExamWorkspaceOpenGroup[] = keys.map((key) => ({
    heading: nameOf(key),
    courseKey: key,
    documents: sorted.filter((entry) => entry.course_key === key),
  }));
  const withoutCourse = sorted.filter((entry) => !entry.course_key);
  if (withoutCourse.length > 0) {
    groups.push({ heading: NO_COURSE, courseKey: null, documents: withoutCourse });
  }
  return groups;
}
