/**
 * Exam workspace question editor AI key line and toolbar AI group.
 *
 * Expected behavior (TASK-SKRIPT-40-04-26 D2, D5):
 *   The question-text toolbar ends with the AI group: Föreslå facit for this
 *   question, undo the AI key and Byt till [typ]. The key line is
 *   information only: an interpreted key names the file's wording, a key the
 *   AI suggested reads "Facit föreslaget av AI" even when the file printed no
 *   key text, and the key line holds no undo button. Undo lives in the toolbar
 *   group and is emitted as `undoAiKey`; it is enabled for an interpreted or
 *   suggested key, disabled for a dropdown (which has no valid keyless state),
 *   and disabled while the question is locked. No automatic-answer glyphs.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { buildGap, choiceItem, gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { withoutAiKey, reviewed, withCorrectChoices } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";
import { provideExamWorkspaceQuestionAi } from "./examWorkspaceQuestionAiKeys";

const AI_UNDO = '[data-test="exam-workspace-ai-undo"]';
const AI_SUGGEST = '[data-test="exam-workspace-ai-suggest"]';
const OLD_KEY_LINE_UNDO = '[data-test="exam-workspace-undo-interpretation"]';
const reviewButton = '[data-test="exam-workspace-review"]';
const keyLine = '[data-test="exam-workspace-original-facit"]';
const FACIT = "Det första alternativet är rätt.";
const RETRY_TITLE = "Föreslå nytt facit · Du kan bara be om ett nytt förslag en gång per fråga.";
const DROPDOWN_UNDO = "Ta bort AI-facit · En lucka med rullista måste ha ett rätt svar.";

function editorProps(item: NativeExamItem, disabled: boolean) {
  return {
    item,
    label: "1",
    origin: "digiexam_import" as const,
    parent: null,
    child: null,
    converting: false,
    disabled,
    notice: null,
    importOpen: false,
  };
}

/**
 * Mount the editor below a workspace that provides the single-question AI
 * harness. The host holds the item in a ref, so a test can move the question to
 * its next state (an undone key, a reviewed key) as the owner would.
 */
function mountEditor(item: NativeExamItem, disabled = false, suggest: (itemId: string) => void = () => undefined) {
  const current = ref<NativeExamItem>(item);
  const Host = defineComponent({
    setup() {
      provideExamWorkspaceQuestionAi({ busy: ref(false), suggest });
      return () => h(ExamWorkspaceQuestionEditor, editorProps(current.value, disabled));
    },
  });
  const root = mount(Host, {
    global: { plugins: [examWorkspaceProvidersPlugin()] },
  });
  return {
    editor: root.findComponent(ExamWorkspaceQuestionEditor),
    setItem: async (next: NativeExamItem) => {
      current.value = next;
      await root.vm.$nextTick();
    },
  };
}

function aiItem(origin: "ai_interpreted" | "machine_proposed"): NativeExamItem {
  return { ...choiceItem("single_choice", origin, ["choice_001"], null), facit_text: FACIT };
}

describe("question editor AI key line", () => {
  it("names the file's wording for an interpreted key and shows the file's facit after undo", async () => {
    const item = aiItem("ai_interpreted");
    const { editor, setItem } = mountEditor(item);

    expect(editor.findAll(keyLine)).toHaveLength(1);
    expect(editor.get(keyLine).text()).toContain("Facit tolkat av AI ur");
    expect(editor.get(keyLine).text()).toContain(FACIT);
    expect(editor.get(keyLine).find(OLD_KEY_LINE_UNDO).exists()).toBe(false);
    expect(editor.find(OLD_KEY_LINE_UNDO).exists()).toBe(false);

    await setItem(withoutAiKey(item));
    expect(editor.get(keyLine).text()).not.toContain("tolkat av AI");
    expect(editor.get(keyLine).text()).toContain(FACIT);
    expect(editor.find<HTMLInputElement>('input[type="radio"]:checked').exists()).toBe(false);
    // The one retry an undo opens: the toolbar now offers Föreslå nytt facit once.
    expect(editor.get(AI_SUGGEST).attributes("title")).toBe(RETRY_TITLE);
  });

  it("reads Facit föreslaget av AI for a suggested key, without quoting the file", () => {
    const { editor } = mountEditor(choiceItem("single_choice", "machine_proposed", ["choice_001"], null));

    expect(editor.get(keyLine).text()).toBe("Facit föreslaget av AI");
    expect(editor.get(keyLine).find("q").exists()).toBe(false);
    expect(editor.get(`${keyLine} .xw-grow`).classes()).toContain("xw-ai");
  });

  it("keeps a suggested key's line even when the file printed key text", () => {
    const { editor } = mountEditor(aiItem("machine_proposed"));

    expect(editor.get(keyLine).text()).toBe("Facit föreslaget av AI");
    expect(editor.get(keyLine).text()).not.toContain(FACIT);
  });

  it("toggles reviewed and drops the AI wording once the teacher reviews the key", async () => {
    const item = aiItem("machine_proposed");
    const { editor, setItem } = mountEditor(item);

    expect(editor.get(reviewButton).attributes("aria-pressed")).toBe("false");
    await editor.get(reviewButton).trigger("click");
    expect(editor.emitted("toggleReviewed")).toHaveLength(1);
    await setItem(reviewed(item));
    expect(editor.get(reviewButton).attributes("aria-pressed")).toBe("true");
    expect(editor.get(keyLine).text()).not.toContain("föreslaget av AI");
  });

  it("loses the AI key line mark when a teacher changes the answer", async () => {
    const item = aiItem("ai_interpreted");
    const { editor, setItem } = mountEditor(item);

    await editor.get('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(true);
    expect(editor.emitted("updateCorrectChoices")).toEqual([[item.item_id, ["choice_002"]]]);
    await setItem(withCorrectChoices(item, ["choice_002"]));
    expect(editor.get(AI_UNDO).attributes("disabled")).toBeDefined();
    expect(editor.get(keyLine).text()).not.toContain("tolkat av AI");
  });
});

describe("question editor toolbar AI group", () => {
  it("asks the provided keys for this question from both the toolbar and the ⋮ row", async () => {
    const suggest = vi.fn();
    const item = choiceItem("single_choice", "absent", [], null);
    const { editor } = mountEditor(item, false, suggest);

    await editor.get(AI_SUGGEST).trigger("click");
    expect(suggest).toHaveBeenNthCalledWith(1, item.item_id);

    await editor.get('[data-test="exam-workspace-more"]').trigger("click");
    await flushPromises();
    const row = document.querySelector<HTMLElement>('[data-test="exam-workspace-more-ai-suggest"]');
    expect(row).not.toBeNull();
    row!.click();
    await flushPromises();
    expect(suggest).toHaveBeenNthCalledWith(2, item.item_id);

    document.body.replaceChildren();
  });

  it("undoes the AI key from the toolbar with undoAiKey", async () => {
    const item = aiItem("machine_proposed");
    const { editor } = mountEditor(item);

    const toolbar = editor.get('[role="toolbar"]');
    const undo = toolbar.get(AI_UNDO);
    expect(undo.attributes("disabled")).toBeUndefined();
    expect(undo.attributes("title")).toBe("Ta bort AI-facit och lämna frågan utan facit");
    await undo.trigger("click");

    expect(editor.emitted("undoAiKey")).toEqual([[item.item_id]]);
  });

  it("disables undo in the toolbar while the question is locked and emits nothing", async () => {
    const { editor } = mountEditor(aiItem("ai_interpreted"), true);

    expect(editor.get(AI_UNDO).attributes("disabled")).toBeDefined();
    expect(editor.get(reviewButton).attributes("disabled")).toBeDefined();
    await editor.get(AI_UNDO).trigger("click");
    expect(editor.emitted("undoAiKey")).toBeUndefined();
  });

  it("offers no undo for a dropdown AI key but keeps it for an interpreted gap_fill", () => {
    const dropdown: NativeExamItem = {
      ...gapItem("ai_interpreted", [], null),
      kind: "inline_choice",
      facit_text: FACIT,
      gaps: [
        buildGap("gap_001", [], {
          correct_option_id: "choice_001",
          options: [
            { choice_id: "choice_001", body: plainBody("röd") },
            { choice_id: "choice_002", body: plainBody("blå") },
          ],
        }),
      ],
    };
    const { editor } = mountEditor(dropdown);
    expect(editor.get(keyLine).text()).toContain("Facit tolkat av AI ur");
    const dropdownUndo = editor.get(AI_UNDO);
    expect(dropdownUndo.attributes("disabled")).toBeDefined();
    expect(dropdownUndo.attributes("title")).toBe(DROPDOWN_UNDO);
    expect(editor.find(AI_SUGGEST).exists()).toBe(false);

    const gapFill = { ...gapItem("ai_interpreted", [["gap_001", ["Stockholm"]]], null), facit_text: FACIT };
    const { editor: gapFillEditor } = mountEditor(gapFill);
    expect(gapFillEditor.get(AI_UNDO).attributes("disabled")).toBeUndefined();
  });
});
