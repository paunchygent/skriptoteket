/** Question editor AI key line, undo and reviewed lifetime; no automatic-answer glyphs. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { reviewed, withCorrectChoices, withoutInterpretedKey } from "./examWorkspaceItemEdits";

function mountEditor(item: NativeExamItem, disabled = false) {
  return mount(ExamWorkspaceQuestionEditor, {
    props: {
      item,
      label: "1",
      origin: "digiexam_import",
      parent: null,
      child: null,
      converting: false,
      disabled,
      notice: null,
      importOpen: false,
      lastChildDeletable: false,
    },
  });
}

const undoButton = '[data-test="exam-workspace-undo-interpretation"]';
const reviewButton = '[data-test="exam-workspace-review"]';
const keyLine = '[data-test="exam-workspace-original-facit"]';
const FACIT = "Det första alternativet är rätt.";

function aiItem(origin: "ai_interpreted" | "machine_proposed"): NativeExamItem {
  return { ...choiceItem("single_choice", origin, ["choice_001"], null), facit_text: FACIT };
}

describe("question editor AI conversion key", () => {
  it("has one AI key line and one undo, then shows the file's facit after undo", async () => {
    const item = aiItem("ai_interpreted");
    const wrapper = mountEditor(item);
    expect(wrapper.findAll(keyLine)).toHaveLength(1);
    expect(wrapper.get(keyLine).text()).toContain("Facit tolkat av AI ur");
    expect(wrapper.get(keyLine).text()).toContain(FACIT);
    await wrapper.get(undoButton).trigger("click");
    expect(wrapper.emitted("undoInterpretation")).toEqual([[item.item_id]]);
    await wrapper.setProps({ item: withoutInterpretedKey(item) });
    expect(wrapper.find(undoButton).exists()).toBe(false);
    expect(wrapper.get(keyLine).text()).not.toContain("tolkat av AI");
    expect(wrapper.get(keyLine).text()).toContain(FACIT);
    expect(wrapper.find<HTMLInputElement>('input[type="radio"]:checked').exists()).toBe(false);
  });

  it("shows an invented key as not reviewed, never offers undo, and toggles reviewed", async () => {
    const item = aiItem("machine_proposed");
    const wrapper = mountEditor(item);
    expect(wrapper.find(undoButton).exists()).toBe(false);
    expect(wrapper.get(reviewButton).attributes("aria-pressed")).toBe("false");
    await wrapper.get(reviewButton).trigger("click");
    expect(wrapper.emitted("toggleReviewed")).toHaveLength(1);
    await wrapper.setProps({ item: reviewed(item) });
    expect(wrapper.get(reviewButton).attributes("aria-pressed")).toBe("true");
    expect(wrapper.get(keyLine).text()).not.toContain("tolkat av AI");
  });

  it("keeps an interpreted key unreviewed even when parse review is complete", async () => {
    const item = aiItem("ai_interpreted");
    item.review = { ...item.review, state: "review_complete" };
    const wrapper = mountEditor(item);
    expect(wrapper.get(reviewButton).attributes("aria-pressed")).toBe("false");
    await wrapper.get(reviewButton).trigger("click");
    expect(wrapper.emitted("toggleReviewed")).toHaveLength(1);
    await wrapper.setProps({ item: reviewed(item) });
    expect(wrapper.get(reviewButton).attributes("aria-pressed")).toBe("true");
    expect(wrapper.find(undoButton).exists()).toBe(false);
  });

  it("loses the AI key line mark when a teacher changes the answer", async () => {
    const item = aiItem("ai_interpreted");
    const wrapper = mountEditor(item);
    await wrapper.get('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(true);
    expect(wrapper.emitted("updateCorrectChoices")).toEqual([[item.item_id, ["choice_002"]]]);
    await wrapper.setProps({ item: withCorrectChoices(item, ["choice_002"]) });
    expect(wrapper.find(undoButton).exists()).toBe(false);
    expect(wrapper.get(keyLine).text()).not.toContain("tolkat av AI");
  });

  it("disables undo and reviewed while the editor is locked", async () => {
    const wrapper = mountEditor(aiItem("ai_interpreted"), true);
    expect(wrapper.get(undoButton).attributes("disabled")).toBeDefined();
    expect(wrapper.get(reviewButton).attributes("disabled")).toBeDefined();
    await wrapper.get(undoButton).trigger("click");
    expect(wrapper.emitted("undoInterpretation")).toBeUndefined();
  });
});
