/**
 * Exam workspace new-exam intake (TASK-SKRIPT-40-04-21).
 *
 * Expected behavior:
 *   `examWorkspaceDraftHasContent` reports the blank shape as empty and every
 *   single content signal as content, so a wrong "empty" never discards a
 *   guest's work.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { blankDocument, keylessItem, textBody } from "../ExamWorkspaceGuestMode.specSupport";
import { examWorkspaceDraftHasContent } from "./examWorkspaceNewExam";

function emptyItem(): NativeExamItem {
  return {
    ...keylessItem(1, "single_choice"),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body: [],
    choices: [],
  };
}

function emptyDraft(): NativeExamDocument {
  return { ...blankDocument(), header: { tags: [] }, instructions: [], title: "", items: [emptyItem()] };
}

describe("examWorkspaceDraftHasContent", () => {
  it("reports the blank shape as empty", () => {
    expect(examWorkspaceDraftHasContent(emptyDraft())).toBe(false);
  });

  it("reports a title, a course or a tag as content", () => {
    expect(examWorkspaceDraftHasContent({ ...emptyDraft(), title: "  Prov 1 " })).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        header: { course: { key: "SVE1", name: "Svenska 1" }, tags: [] },
      }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        header: { tags: [{ id: "tag-1", origin: "teacher", question_ids: [], text: "Repetition" }] },
      }),
    ).toBe(true);
  });

  it("reports instructions, a part or an asset as content", () => {
    expect(
      examWorkspaceDraftHasContent({ ...emptyDraft(), instructions: textBody("Läs noga.") }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        parents: [{ instruction: [], item_ids: [], parent_id: "parent-1", place: 0, printed_total: null }],
      }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        assets: [{ asset_id: "asset-1", byte_length: 10, media_type: "image/png", sha256: "abc" }],
      }),
    ).toBe(true);
  });

  it("reports anything but exactly one empty question as content", () => {
    expect(examWorkspaceDraftHasContent({ ...emptyDraft(), items: [] })).toBe(true);
    expect(
      examWorkspaceDraftHasContent({ ...emptyDraft(), items: [emptyItem(), emptyItem()] }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({ ...emptyDraft(), items: [{ ...emptyItem(), body: textBody("Fråga?") }] }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        items: [{ ...emptyItem(), choices: [{ body: textBody("A"), choice_id: "choice-1" }] }],
      }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        items: [{ ...emptyItem(), facit_text: "Svaret." }],
      }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        items: [{ ...emptyItem(), criteria: [{ points: 1, text: "Kriterium" }] }],
      }),
    ).toBe(true);
  });

  it("reports gaps, kept gaps and match entries as content", () => {
    const gap = {
      accepted_values: ["svar"],
      automatic_values: [],
      correct_option_id: null,
      excluded_automatic_values: [],
      gap_id: "gap-1",
      options: [],
    };
    expect(
      examWorkspaceDraftHasContent({ ...emptyDraft(), items: [{ ...emptyItem(), gaps: [gap] }] }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({ ...emptyDraft(), items: [{ ...emptyItem(), kept_gaps: [gap] }] }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        items: [{ ...emptyItem(), match_left: [{ body: textBody("Vänster"), left_id: "left-1" }] }],
      }),
    ).toBe(true);
    expect(
      examWorkspaceDraftHasContent({
        ...emptyDraft(),
        items: [{ ...emptyItem(), match_right: [{ body: textBody("Höger"), right_id: "right-1" }] }],
      }),
    ).toBe(true);
  });
});
