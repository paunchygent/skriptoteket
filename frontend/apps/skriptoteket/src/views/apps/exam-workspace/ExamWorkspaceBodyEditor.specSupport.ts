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
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

export function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
    body: [
      { heading_level: null, segments: [
          { kind: "text", marks: [], text: "Vatten kokar vid " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " grader och fryser vid " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: " grader." },
        ],
      },
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Se " }, { asset_id: "asset_001", kind: "asset" }] },
    ],
    choices: [],
    gaps: [
      buildGap("gap_001", ["100"]),
      buildGap("gap_002"),
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
    tick_points: null,
    ...overrides,
  };
}

export function mountEditor(item: NativeExamItem = buildGapItem()) {
  return mount(ExamWorkspaceBodyEditor, { props: { item }, attachTo: document.body });
}

export function paragraph(wrapper: ReturnType<typeof mountEditor>, index: number): HTMLElement {
  return wrapper.get(`[data-test="exam-workspace-body-paragraph-${index}"]`).element as HTMLElement;
}
