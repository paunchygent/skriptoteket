/**
 * Exam workspace question editor, suggested type.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D2):
 *   A stored `suggested_kind` that differs from the question's type shows
 *   "Byt till [typ]" as the question-text toolbar AI group's last control,
 *   which changes the type in one click, and marks the same entry Förslag in
 *   Byt frågetyp. The type name is the control's face; the whole sentence is
 *   its title and accessible name, so the head no longer holds the button. A
 *   suggestion equal to the current type, or none, shows neither.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { provideExamWorkspaceQuestionAi } from "./examWorkspaceQuestionAiKeys";

const SUGGESTED = '[data-test="exam-workspace-suggested-type"]';
const SUGGEST = '[data-test="exam-workspace-ai-suggest"]';

function freeTextItem(suggested: NativeExamItemKind | null): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    suggested_kind: suggested,
  };
}

const mounted: Array<{ unmount: () => void }> = [];

function editorProps(item: NativeExamItem) {
  return {
    item,
    label: "11",
    origin: "docx_import" as const,
    parent: null,
    child: null,
    converting: false,
    disabled: false,
    notice: null,
    importOpen: false,
  };
}

function mountEditor(item: NativeExamItem) {
  const wrapper = mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
    global: { plugins: [examWorkspaceProvidersPlugin()] },
    props: editorProps(item),
  });
  mounted.push(wrapper);
  return wrapper;
}

/** Mount the editor below a workspace that provides the single-question AI harness. */
function mountEditorWithAi(item: NativeExamItem) {
  const suggest = () => undefined;
  const Host = defineComponent({
    setup() {
      provideExamWorkspaceQuestionAi({ busy: ref(false), suggest });
      return () => h(ExamWorkspaceQuestionEditor, editorProps(item));
    },
  });
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: { plugins: [examWorkspaceProvidersPlugin()] },
  });
  mounted.push(wrapper);
  return wrapper.findComponent(ExamWorkspaceQuestionEditor);
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionEditor suggested type", () => {
  it("offers the stored suggested type inside the toolbar and changes the type in one click", async () => {
    const wrapper = mountEditor(freeTextItem("gap_fill"));

    const toolbar = wrapper.get('[role="toolbar"]');
    const offer = toolbar.get(SUGGESTED);
    expect(offer.text()).toBe("Lucktext");
    expect(offer.attributes("aria-label")).toBe("Byt till Lucktext");
    expect(offer.attributes("title")).toBe("Byt till Lucktext");
    await offer.trigger("click");
    expect(wrapper.emitted("changeType")).toEqual([["gap_fill"]]);

    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    const marked = [...document.querySelectorAll('[data-test="exam-workspace-type-suggested"]')];
    expect(marked).toHaveLength(1);
    expect(marked[0]!.closest('[data-test="exam-workspace-type-gap_fill"]')).not.toBeNull();
  });

  it("shows the AI group's suggest control inside the same toolbar, as the bar's last group", () => {
    const wrapper = mountEditorWithAi(choiceItem("single_choice", "absent", [], null));

    const toolbar = wrapper.get('[role="toolbar"]');
    expect(toolbar.find(SUGGEST).exists()).toBe(true);
    expect(toolbar.find('[data-test="exam-workspace-ai-undo"]').exists()).toBe(true);
    expect(toolbar.element.lastElementChild?.classList.contains("qai")).toBe(true);
  });

  it("puts the same group in a Kort svar question's toolbar", () => {
    const wrapper = mountEditorWithAi(newTeacherItem("item_001", 1, "short_answer"));

    expect(wrapper.find('[data-test="exam-workspace-short-answer"]').exists()).toBe(true);
    const toolbar = wrapper.get('[role="toolbar"]');
    expect(toolbar.find(SUGGEST).exists()).toBe(true);
    expect(toolbar.element.lastElementChild?.classList.contains("qai")).toBe(true);
  });

  it.each([["free_text" as const], [null]])("offers nothing for the suggestion %s", async (suggested) => {
    const wrapper = mountEditor(freeTextItem(suggested));

    expect(wrapper.find(SUGGESTED).exists()).toBe(false);
    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    expect(document.querySelector('[data-test="exam-workspace-type-suggested"]')).toBeNull();
  });
});
