/** Item-level AI status, undo and reviewed lifetime; no automatic-answer glyphs. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { reviewed, withCorrectChoices, withoutInterpretedKey } from "./examWorkspaceItemEdits";

function mountEditor(item: NativeExamItem, disabled = false) {
  return mount(ExamWorkspaceItemEditor, {
    props: { attentionCount: 0, detailsOpen: false, disabled, item, position: 1, showNavigation: false, total: 1 },
  });
}

const aiStatus = '[data-test="exam-workspace-editor-ai-key"]';
const undoButton = '[data-test="exam-workspace-undo-interpretation"]';
const reviewButton = '[data-test="exam-workspace-mark-reviewed"]';
const facit = '[data-test="exam-workspace-original-facit"]';

describe("item editor AI conversion key", () => {
  it("has one accessible glyph and one undo, then shows the retained facit after undo", async () => {
    const item = { ...choiceItem("single_choice", "ai_interpreted", ["choice_001"], null), facit_text: "Det första alternativet är rätt." };
    const wrapper = mountEditor(item);
    expect(wrapper.findAll(aiStatus)).toHaveLength(1);
    expect(wrapper.get(aiStatus).attributes("aria-label")).toBe("Tolkad av AI");
    expect(wrapper.find(facit).exists()).toBe(false);
    await wrapper.get(undoButton).trigger("click");
    expect(wrapper.emitted("undoInterpretation")).toEqual([[item.item_id]]);
    await wrapper.setProps({ item: withoutInterpretedKey(item) });
    expect(wrapper.find(aiStatus).exists()).toBe(false);
    expect(wrapper.find(undoButton).exists()).toBe(false);
    expect(wrapper.get(facit).text()).toContain(item.facit_text);
    expect(wrapper.find<HTMLInputElement>('input[type="radio"]:checked').exists()).toBe(false);
  });

  it("shows invented key glyph together with review warning, never undo", async () => {
    const item = choiceItem("single_choice", "machine_proposed", ["choice_001"], null);
    const wrapper = mountEditor(item);
    expect(wrapper.get(aiStatus).attributes("aria-label")).toBe("Förslag från AI");
    expect(wrapper.get('[data-test="exam-workspace-review-badge"]').text()).toContain("Behöver granskas");
    expect(wrapper.find(undoButton).exists()).toBe(false);
    await wrapper.get(reviewButton).trigger("click");
    expect(wrapper.emitted("markReviewed")).toEqual([[item.item_id]]);
    await wrapper.setProps({ item: reviewed(item) });
    expect(wrapper.find(aiStatus).exists()).toBe(false);
  });

  it("offers reviewed on an interpreted key even when parse review is complete", async () => {
    const item = choiceItem("single_choice", "ai_interpreted", ["choice_001"], null);
    item.review = { ...item.review, state: "review_complete" };
    const wrapper = mountEditor(item);
    await wrapper.get(reviewButton).trigger("click");
    expect(wrapper.emitted("markReviewed")).toEqual([[item.item_id]]);
    await wrapper.setProps({ item: reviewed(item) });
    expect(wrapper.find(aiStatus).exists()).toBe(false);
    expect(wrapper.find(undoButton).exists()).toBe(false);
  });

  it("loses the glyph when a teacher changes the answer", async () => {
    const item = choiceItem("single_choice", "ai_interpreted", ["choice_001"], null);
    const wrapper = mountEditor(item);
    await wrapper.get('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(true);
    expect(wrapper.emitted("updateCorrectChoices")).toEqual([[item.item_id, ["choice_002"]]]);
    await wrapper.setProps({ item: withCorrectChoices(item, ["choice_002"]) });
    expect(wrapper.find(aiStatus).exists()).toBe(false);
  });

  it("disables undo and reviewed while the editor is locked", async () => {
    const wrapper = mountEditor(choiceItem("single_choice", "ai_interpreted", ["choice_001"], null), true);
    expect(wrapper.get(undoButton).attributes("disabled")).toBeDefined();
    expect(wrapper.get(reviewButton).attributes("disabled")).toBeDefined();
    await wrapper.get(undoButton).trigger("click");
    expect(wrapper.emitted("undoInterpretation")).toBeUndefined();
  });
});
