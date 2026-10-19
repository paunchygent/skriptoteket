/**
 * Exam workspace question editor, Skrivyta (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   A free-text question shows its writing-area stepper and the apply-to-all
 *   popover, which emit the question's id with the new count and, on confirm,
 *   the count for every free-text question. The popover is fed the free-text
 *   summary the pane passes; another kind shows no writing-area field.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import type { FreeTextWritingLines } from "./examWorkspaceWritingLines";

const FIELD = '[data-test="exam-workspace-writing-lines"]';
const PLUS = '[data-test="exam-workspace-writing-lines-plus"]';
const APPLY_ALL = '[data-test="exam-workspace-writing-lines-apply-all"]';
const CONFIRM = '[data-test="exam-workspace-writing-lines-apply-confirm"]';
const POPOVER = '[data-test="exam-workspace-writing-lines-popover"]';

function mountEditor(item: NativeExamItem, freeTextWritingLines: FreeTextWritingLines[] = []) {
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
      freeTextWritingLines,
    },
    global: {
      plugins: [examWorkspaceProvidersPlugin()],
    },
  });
}

describe("ExamWorkspaceQuestionEditor Skrivyta", () => {
  it("shows the writing-area field on a free-text question", () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: 8 }));

    expect(wrapper.get(FIELD).text()).toContain("Skrivyta");
    expect(wrapper.get(FIELD).text()).toContain("8 rader");
  });

  it("emits the count from one question and, on confirm, for every free-text question", async () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: 8 }), [
      { itemId: "item_001", label: "1", lines: 8 },
      { itemId: "item_002", label: "2", lines: 4 },
    ]);

    await wrapper.get(PLUS).trigger("click");
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(CONFIRM).trigger("click");

    expect(wrapper.emitted("updateWritingLines")).toEqual([["item_001", 9]]);
    expect(wrapper.emitted("applyWritingLinesToAll")).toEqual([[8]]);
  });

  it("passes the free-text summary to the popover", async () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: 8 }), [
      { itemId: "item_001", label: "1a", lines: 8 },
      { itemId: "item_002", label: "1b", lines: 4 },
      { itemId: "item_003", label: "2", lines: null },
    ]);

    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.get(POPOVER).text()).toContain("Alla 3 fritextfrågor får 8 rader.");
    expect(wrapper.get(POPOVER).text()).toContain("1b och 2 har i dag en annan skrivyta.");
  });

  it("shows no writing-area field on a free-text question without a count", () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: null }));

    expect(wrapper.find(FIELD).exists()).toBe(false);
  });

  it("shows no writing-area field on a single-choice question", () => {
    const wrapper = mountEditor(choiceItem("single_choice", "source_provided", ["choice_001"], null));

    expect(wrapper.find(FIELD).exists()).toBe(false);
  });
});
