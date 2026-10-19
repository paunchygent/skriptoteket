/** Progressive delivery must not undo a teacher's course choice or explicit clear. */
import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { mergeConversionRevision } from "./examWorkspaceConversionMerge";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";

const svenska = { key: "SVESVE02", name: "Svenska 2" };
const engelska = { key: "ENGENG05", name: "Engelska 5" };

function document(course: NativeExamDocument["header"]["course"]): NativeExamDocument {
  return { ...buildParentDocument(), header: { course, course_hint: "Svenska 2", printed_total: 36, printed_total_dismissed: false, tags: [] } };
}

describe("course during progressive header replacement", () => {
  it.each([
    { name: "teacher picks a different course", initial: null, picked: engelska },
    { name: "teacher clears a preselected course", initial: svenska, picked: null },
  ])("retains the whole teacher header when $name across two delivered revisions", ({ initial, picked }) => {
    const base = document(initial);
    const local = { ...base, header: { ...base.header, course: picked } };
    const head = { ...document(svenska), revision: 2, header: { ...document(svenska).header, printed_total: 40 } };
    const merged = mergeConversionRevision({ base, local, head, baseUnits: [], headUnits: [] });
    const next = mergeConversionRevision({
      base: head, local: merged, head: { ...head, revision: 3 }, baseUnits: [], headUnits: [],
    });
    expect(merged.header).toEqual(local.header);
    expect(next.header).toEqual(local.header);
    expect(next.revision).toBe(3);
  });

  it("adopts an automatically selected course if the teacher has not changed the header", () => {
    const base = document(null);
    const head = { ...document(svenska), revision: 2 };
    const merged = mergeConversionRevision({ base, local: base, head, baseUnits: [], headUnits: [] });
    expect(merged.header.course).toEqual(svenska);
  });
});
