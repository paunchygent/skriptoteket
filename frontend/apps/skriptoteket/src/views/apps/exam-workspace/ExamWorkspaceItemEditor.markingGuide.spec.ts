/**
 * Exam workspace item editor, marking guide and type-check mark.
 *
 * Expected behavior:
 *   A free-text item shows the "Rättningsmall" textarea with its stored guide;
 *   typing emits the text, emptying the field emits null; a choice item shows
 *   no such field. A review confidence below 0.95 shows the quiet "Kontrollera
 *   frågetypen" mark; 0.95 and null show none.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const GUIDE_INPUT = '[data-test="exam-workspace-marking-guide-input"]';
const TYPE_MARK = '[data-test="exam-workspace-type-uncertain"]';

function buildFreeTextItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    marking_guide: null,
    ...overrides,
  };
}

function mountEditor(item: NativeExamItem) {
  return mount(ExamWorkspaceItemEditor, {
    props: {
      attentionCount: 0,
      detailsOpen: false,
      item,
      position: 1,
      showNavigation: false,
      total: 1,
    },
  });
}

describe("ExamWorkspaceItemEditor marking guide", () => {
  it("shows the stored guide in a labelled multi-line field for a free-text item", () => {
    const wrapper = mountEditor(buildFreeTextItem({ marking_guide: "2 p för definitionen" }));

    const field = wrapper.get<HTMLTextAreaElement>(GUIDE_INPUT);
    expect(field.element.tagName).toBe("TEXTAREA");
    expect(field.element.value).toBe("2 p för definitionen");
    expect(wrapper.text()).toContain("Rättningsmall");
  });

  it("emits the typed text, and null once the field is emptied", async () => {
    const wrapper = mountEditor(buildFreeTextItem());

    await wrapper.get(GUIDE_INPUT).setValue("1 p per exempel\n1 p för motivering");
    await wrapper.get(GUIDE_INPUT).setValue("  \n ");

    expect(wrapper.emitted("updateMarkingGuide")).toEqual([
      ["item_001", "1 p per exempel\n1 p för motivering"],
      ["item_001", null],
    ]);
  });

  it("shows no marking guide field on a choice or matching item", () => {
    expect(mountEditor(buildMatchingItem()).find(GUIDE_INPUT).exists()).toBe(false);
  });

  it("marks a type below 0.95 confidence for checking, without blocking", () => {
    const wrapper = mountEditor(
      buildFreeTextItem({
        review: { confidence: 0.9, parse_origin: "llm_parsed", reasons: [], state: "review_complete" },
      }),
    );

    expect(wrapper.get(TYPE_MARK).text()).toBe("Kontrollera frågetypen");
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
