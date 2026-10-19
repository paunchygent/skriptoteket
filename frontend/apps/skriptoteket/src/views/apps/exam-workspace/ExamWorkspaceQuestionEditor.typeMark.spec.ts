/**
 * Exam workspace question editor, type-check mark.
 *
 * Expected behavior:
 *   A review confidence below 0.95 shows the "Kontrollera frågetypen."
 *   hint; 0.95 and null show none. A question the conversion could not build
 *   (review required after a deterministic parse, the server's export rule)
 *   reads "Ej konverterad" and hides its answer fields, as the list does.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
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
    global: { plugins: [examWorkspaceProvidersPlugin()] },
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

describe("ExamWorkspaceQuestionEditor unbuilt question", () => {
  it("follows the list and the server: review required after a deterministic parse is unbuilt", () => {
    const wrapper = mountEditor(
      buildFreeTextItem({
        review: { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" },
      }),
    );

    expect(wrapper.get('[data-test="exam-workspace-type"]').text()).toContain("Ej konverterad");
    expect(wrapper.find('[data-test="exam-workspace-criterion-add"]').exists()).toBe(false);
  });

  it("keeps a reviewed deterministic question built", () => {
    const wrapper = mountEditor(
      buildFreeTextItem({
        review: { confidence: null, parse_origin: "deterministic", reasons: [], state: "review_complete" },
      }),
    );

    expect(wrapper.get('[data-test="exam-workspace-type"]').text()).not.toContain("Ej konverterad");
    expect(wrapper.find('[data-test="exam-workspace-criterion-add"]').exists()).toBe(true);
  });
});
