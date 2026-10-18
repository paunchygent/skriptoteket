/**
 * Exam workspace question editor, Skrivyta (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   A free-text question shows its writing-area stepper and the apply-to-all
 *   action, which emit the question's id with the new count and the shared
 *   count; another kind shows no writing-area field.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";

const FIELD = '[data-test="exam-workspace-writing-lines"]';
const PLUS = '[data-test="exam-workspace-writing-lines-plus"]';
const APPLY_ALL = '[data-test="exam-workspace-writing-lines-apply-all"]';

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
    },
  });
}

describe("ExamWorkspaceQuestionEditor Skrivyta", () => {
  it("shows the writing-area field on a free-text question", () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: 8 }));

    expect(wrapper.get(FIELD).text()).toContain("Skrivyta: 8 rader");
  });

  it("emits the count from one question and for every free-text question", async () => {
    const wrapper = mountEditor(buildFreeTextItem(1, { writing_lines: 8 }));

    await wrapper.get(PLUS).trigger("click");
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.emitted("updateWritingLines")).toEqual([["item_001", 9]]);
    expect(wrapper.emitted("applyWritingLinesToAll")).toEqual([[8]]);
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
