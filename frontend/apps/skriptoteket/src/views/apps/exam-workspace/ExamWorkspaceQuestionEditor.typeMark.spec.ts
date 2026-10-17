/**
 * Exam workspace question editor, type-check mark.
 *
 * Expected behavior:
 *   A review confidence below 0.95 shows the "Kontrollera frågetypen."
 *   hint; 0.95 and null show none.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const TYPE_MARK = '[data-test="exam-workspace-type-uncertain"]';

function buildFreeTextItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    ...overrides,
  };
}

function mountEditor(item: NativeExamItem) {
  return mount(ExamWorkspaceQuestionEditor, {
    props: {
      item,
      label: "1",
      origin: "digiexam_import",
      parent: null,
      child: null,
      converting: false,
      disabled: false,
      notice: null,
      importOpen: false,
      lastChildDeletable: false,
    },
  });
}

describe("ExamWorkspaceQuestionEditor type-check mark", () => {
  it("marks a type below 0.95 confidence for checking, without blocking", () => {
    const wrapper = mountEditor(
      buildFreeTextItem({
        review: { confidence: 0.9, parse_origin: "llm_parsed", reasons: [], state: "review_complete" },
      }),
    );

    expect(wrapper.get(TYPE_MARK).text()).toContain("Kontrollera frågetypen");
    expect(wrapper.find(`${TYPE_MARK} button`).exists()).toBe(false);
  });

  it.each([0.95, 1, null])("shows no type mark at confidence %s", (confidence) => {
    const wrapper = mountEditor(
      buildFreeTextItem({
        review: { confidence, parse_origin: "llm_parsed", reasons: [], state: "review_complete" },
      }),
    );

    expect(wrapper.find(TYPE_MARK).exists()).toBe(false);
  });
});
