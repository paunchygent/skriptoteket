/**
 * Exam workspace question-text editor spec support.
 *
 * Purpose:
 *   Shared fixture and mount helpers for the `ExamWorkspaceBodyEditor` specs:
 *   a gap-fill item with two gaps (one keyed, one empty) and an image marker,
 *   a mounted editor attached to the document, and a paragraph lookup.
 */

import { mount } from "@vue/test-utils";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";

export function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
    body: [
      {
        segments: [
          { kind: "text", text: "Vatten kokar vid " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", text: " grader och fryser vid " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", text: " grader." },
        ],
      },
      { segments: [{ kind: "text", text: "Se " }, { asset_id: "asset_001", kind: "asset" }] },
    ],
    choices: [],
    gaps: [
      { accepted_values: ["100"], gap_id: "gap_001" },
      { accepted_values: [], gap_id: "gap_002" },
    ],
    item_id: "item_001",
    kind: "gap_fill",
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    title: null,
    ...overrides,
  };
}

export function mountEditor(item: NativeExamItem = buildGapItem()) {
  return mount(ExamWorkspaceBodyEditor, { props: { item }, attachTo: document.body });
}

export function paragraph(wrapper: ReturnType<typeof mountEditor>, index: number): HTMLElement {
  return wrapper.get(`[data-test="exam-workspace-body-paragraph-${index}"]`).element as HTMLElement;
}
