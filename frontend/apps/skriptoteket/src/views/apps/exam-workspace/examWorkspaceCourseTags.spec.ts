/**
 * Exam workspace course-tag rule: choosing a course keeps only its ticks.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, ticks defect):
 *   Centralt innehåll ticks are exam metadata that categorise the exam, not
 *   grading criteria. A tick belongs to the chosen course through its
 *   `<course_key>:` id prefix. Choosing another course keeps only the ticks
 *   the new course owns; clearing the course keeps none; the unchanged course
 *   key returns the document itself, so the caller makes no edit. Other
 *   header fields stay untouched.
 */

import { describe, expect, it } from "vitest";

import type { ExamCourseChoice, NativeExamDocument } from "../../../api/examWorkspace";
import { applyCourseChange } from "./examWorkspaceCourseTags";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";

const SVE: ExamCourseChoice = { key: "SVESVE02", name: "Svenska 2" };
const OTHER: ExamCourseChoice = { key: "MATMAT02", name: "Matematik 2" };

function tagged(): NativeExamDocument {
  const base = exam("Prov", 2);
  return {
    ...base,
    header: {
      ...base.header,
      course: SVE,
      tags: [
        { id: "SVESVE02:cen-1", origin: "teacher", question_ids: [], text: "Centralt 1" },
        { id: "OTHER:x", origin: "teacher", question_ids: [], text: "Främmande" },
        { id: "SVESVE02:cen-2", origin: "teacher", question_ids: [], text: "Centralt 2" },
      ],
    },
  };
}

describe("applyCourseChange", () => {
  it("clearing the course keeps no tags", () => {
    const next = applyCourseChange(tagged(), null);

    expect(next.header.course).toBeNull();
    expect(next.header.tags).toEqual([]);
  });

  it("choosing another course keeps only the ticks the new course owns", () => {
    const next = applyCourseChange(tagged(), OTHER);

    expect(next.header.course).toEqual(OTHER);
    expect(next.header.tags).toEqual([]);
  });

  it("choosing the course that owns the ticks keeps them, in order", () => {
    const base = tagged();
    const document = {
      ...base,
      header: { ...base.header, course: OTHER },
    };
    const next = applyCourseChange(document, { ...SVE });

    expect(next.header.course).toEqual(SVE);
    expect(next.header.tags.map((item) => item.id)).toEqual(["SVESVE02:cen-1", "SVESVE02:cen-2"]);
  });

  it("returns the document itself when the course key is unchanged", () => {
    const document = tagged();

    expect(applyCourseChange(document, { ...SVE })).toBe(document);
  });

  it("returns the document itself when null stays null", () => {
    const base = exam("Prov", 2);
    const document = { ...base, header: { ...base.header, course: null, tags: [] } };

    expect(applyCourseChange(document, null)).toBe(document);
  });

  it("keeps the other header fields and never mutates the original", () => {
    const base = tagged();
    const document = {
      ...base,
      header: { ...base.header, course_hint: "Svenska", printed_total: 42 },
    };
    const before = document.header.tags.map((item) => item.id);

    const next = applyCourseChange(document, null);

    expect(next.header.course_hint).toBe("Svenska");
    expect(next.header.printed_total).toBe(42);
    expect(document.header.tags.map((item) => item.id)).toEqual(before);
  });
});
