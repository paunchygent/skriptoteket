/**
 * Exam workspace choice field.
 *
 * Expected behavior:
 *   Each option edits on the shared editor like a word processor: a selection
 *   across two paragraphs deletes with Backspace and merges them, Enter adds a
 *   paragraph and Shift+Enter a line break. Clearing an option emits the empty
 *   body without a refusal, and the option stays empty and marked until the
 *   teacher writes again. A locked field is not editable and emits nothing.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceChoiceField from "./ExamWorkspaceChoiceField.vue";
import {
  editorBehind,
  posIn,
  press,
  settleEditors,
  surfaceOf,
} from "./ExamWorkspaceRichTextEntry.specSupport";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

const OPTION_1 = "exam-workspace-choice-text-choice_001";
const OPTION_2 = "exam-workspace-choice-text-choice_002";

function paragraph(text: string): NativeExamBodyParagraph {
  return { heading_level: null, segments: [{ kind: "text", marks: [], text }] };
}

function buildItem(first: NativeExamBodyParagraph[]): NativeExamItem {
  return {
    ...choiceItem("single_choice", "source_provided", ["choice_001"], null, ["choice_001", "choice_002"]),
    choices: [
      { choice_id: "choice_001", body: first },
      { choice_id: "choice_002", body: plainBody("Andra") },
    ],
  };
}

let mounted: VueWrapper | null = null;

async function mountField(item: NativeExamItem, disabled = false): Promise<VueWrapper> {
  mounted = mount(ExamWorkspaceChoiceField, { attachTo: document.body, props: { item, disabled } });
  await settleEditors();
  return mounted;
}

function emittedBodies(wrapper: VueWrapper): Array<[string, NativeExamBodyParagraph[], boolean]> {
  return (wrapper.emitted("updateBody") ?? []) as Array<[string, NativeExamBodyParagraph[], boolean]>;
}

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

describe("ExamWorkspaceChoiceField", () => {
  it("merges two paragraphs when a selection across them is deleted", async () => {
    const wrapper = await mountField(buildItem([paragraph("första"), paragraph("andra")]));
    const editor = editorBehind(wrapper, OPTION_1);
    editor.commands.setTextSelection({
      from: posIn(editor, "första", 3),
      to: posIn(editor, "andra", 2),
    });

    press(surfaceOf(wrapper, OPTION_1), "Backspace");

    expect(emittedBodies(wrapper)).toEqual([["choice_001", [paragraph("fördra")], true]]);
  });

  it("adds a paragraph on Enter and a line break inside the paragraph on Shift+Enter", async () => {
    const wrapper = await mountField(buildItem([paragraph("abcd")]));
    const editor = editorBehind(wrapper, OPTION_1);

    editor.commands.setTextSelection(posIn(editor, "abcd", 2));
    press(surfaceOf(wrapper, OPTION_1), "Enter");
    expect(emittedBodies(wrapper).at(-1)).toEqual(["choice_001", [paragraph("ab"), paragraph("cd")], false]);

    await wrapper.setProps({ item: buildItem([paragraph("abcd")]) });
    editor.commands.setTextSelection(posIn(editor, "abcd", 2));
    press(surfaceOf(wrapper, OPTION_1), "Enter", { shiftKey: true });
    expect(emittedBodies(wrapper).at(-1)).toEqual(["choice_001", [paragraph("ab\ncd")], false]);
  });

  it("emits the empty body when the option is cleared and keeps it empty and marked", async () => {
    const wrapper = await mountField(buildItem([paragraph("Första")]));
    editorBehind(wrapper, OPTION_1).commands.selectAll();

    press(surfaceOf(wrapper, OPTION_1), "Backspace");
    expect(emittedBodies(wrapper)).toEqual([["choice_001", [], false]]);
    expect(wrapper.find('[data-test="exam-workspace-choice-text-hint"]').exists()).toBe(false);

    await wrapper.setProps({ item: buildItem([]) });
    surfaceOf(wrapper, OPTION_1).blur();
    await settleEditors();

    expect(editorBehind(wrapper, OPTION_1).getText()).toBe("");
    expect(emittedBodies(wrapper)).toHaveLength(1);
    expect(surfaceOf(wrapper, OPTION_1).getAttribute("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-choice-text-hint"]');
    expect(surfaceOf(wrapper, OPTION_1).getAttribute("aria-describedby")).toBe(hint.attributes("id"));
    expect(surfaceOf(wrapper, OPTION_2).hasAttribute("aria-invalid")).toBe(false);
  });

  it("is not editable and emits nothing while locked", async () => {
    const wrapper = await mountField(buildItem([paragraph("Första")]), true);
    editorBehind(wrapper, OPTION_1).commands.selectAll();

    press(surfaceOf(wrapper, OPTION_1), "Backspace");

    expect(surfaceOf(wrapper, OPTION_1).getAttribute("contenteditable")).toBe("false");
    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });
});
