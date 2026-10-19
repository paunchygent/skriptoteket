/**
 * Exam workspace whole-document field commands: the course choice.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, ticks defect):
 *   `setCourse` is one `editDocument` call next to `setTags`: clearing the
 *   course drops the working copy's Centralt innehåll ticks at once (the
 *   client applies the backend tag rule), choosing another course keeps only
 *   the ticks the new course owns, and choosing the course already set makes
 *   no edit at all.
 */

import { describe, expect, it } from "vitest";

import type {
  ExamCourseChoice,
  NativeExamContentTag,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useExamWorkspaceDocumentFields } from "./useExamWorkspaceDocumentFields";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";

const SVE: ExamCourseChoice = { key: "SVESVE02", name: "Svenska 2" };

function tagged(): NativeExamDocument {
  const base = exam("Prov", 2);
  return {
    ...base,
    header: {
      ...base.header,
      course: SVE,
      tags: [
        { id: "SVESVE02:cen-1", origin: "teacher", question_ids: [], text: "Centralt 1" },
        { id: "MATMAT02:x", origin: "teacher", question_ids: [], text: "Främmande" },
      ],
    },
  };
}

function mountFields(initial: NativeExamDocument) {
  let current = initial;
  const calls: { structural: boolean }[] = [];
  const fields = useExamWorkspaceDocumentFields({
    courseKey: () => current.header.course?.key ?? null,
    editDocument: (edit, _selectId = null, structural = true) => {
      calls.push({ structural });
      current = edit(current);
      return true;
    },
  });
  return {
    calls,
    current: () => current,
    fields,
  };
}

describe("the course field command", () => {
  it("clearing the course drops the ticks in one structural edit", () => {
    const mounted = mountFields(tagged());

    mounted.fields.setCourse(null);

    expect(mounted.calls).toEqual([{ structural: true }]);
    expect(mounted.current().header.course).toBeNull();
    expect(mounted.current().header.tags).toEqual([]);
  });

  it("choosing another course keeps only the ticks the new course owns", () => {
    const mounted = mountFields(tagged());

    mounted.fields.setCourse({ key: "MATMAT02", name: "Matematik 2" });

    expect(mounted.calls).toEqual([{ structural: true }]);
    expect(mounted.current().header.course).toEqual({ key: "MATMAT02", name: "Matematik 2" });
    expect(mounted.current().header.tags.map((item) => item.id)).toEqual(["MATMAT02:x"]);
  });

  it("choosing the course already set makes no edit", () => {
    const mounted = mountFields(tagged());

    mounted.fields.setCourse({ key: "SVESVE02", name: "Svenska 2" });

    expect(mounted.calls).toEqual([]);
  });

  it("setTags still replaces only the ticks in one structural edit", () => {
    const mounted = mountFields(tagged());
    const tags: NativeExamContentTag[] = [
      { id: "SVESVE02:cen-9", origin: "teacher", question_ids: [], text: "Centralt 9" },
    ];

    mounted.fields.setTags(tags);

    expect(mounted.calls).toEqual([{ structural: true }]);
    expect(mounted.current().header.course).toEqual(SVE);
    expect(mounted.current().header.tags.map((item) => item.id)).toEqual(["SVESVE02:cen-9"]);
  });
});
