/**
 * Exam workspace question editor, shared rich-text formatting target.
 *
 * Expected behavior:
 *   The item editor has one formatting toolbar and one active rich target: the
 *   question text, choice option or Kategorisera entry that last had focus.
 *   ProseMirror keeps each editor's own selection, so a glyph edits the text
 *   the teacher is in and never a stale surface: not the question after focus
 *   moved to an option, not the first option after focus moved to the second,
 *   not an entry of the previous item, and not an entry that was removed.
 *   Superscript, subscript and heading glyphs reach the focused entry, and a
 *   locked editor emits nothing.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  editorBehind,
  selectText,
  settleEditors,
  surfaceOf,
} from "./ExamWorkspaceRichTextEntry.specSupport";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { plainBody } from "./examWorkspaceRichText";

let mounted: VueWrapper | null = null;

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

async function mountEditor(item: NativeExamItem, disabled = false): Promise<VueWrapper> {
  mounted = mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
    global: { plugins: [examWorkspaceProvidersPlugin()] },
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
    },
  });
  await settleEditors();
  return mounted;
}

const QUESTION = "exam-workspace-body-editor-surface";
const OPTION_1 = "exam-workspace-choice-text-choice_001";
const OPTION_2 = "exam-workspace-choice-text-choice_002";
const MATCH_LEFT = "exam-workspace-match-left-text-left_001";
const BOLD = '[data-test="exam-workspace-body-mark-bold"]';
const SUPERSCRIPT = '[data-test="exam-workspace-body-mark-superscript"]';
const SUBSCRIPT = '[data-test="exam-workspace-body-mark-subscript"]';
const HEADING_2 = '[data-test="exam-workspace-body-heading-2"]';

function buildChoiceWithText(): NativeExamItem {
  return {
    ...choiceItem("single_choice", "source_provided", [], null, ["choice_001", "choice_002"]),
    body: plainBody("Question"),
    choices: [
      { choice_id: "choice_001", body: plainBody("Option") },
      { choice_id: "choice_002", body: plainBody("Other") },
    ],
  };
}

/** Put the caret into a surface and select `needle`, the way a teacher clicks and drags. */
function selectIn(wrapper: VueWrapper, testId: string, needle: string): void {
  surfaceOf(wrapper, testId).focus();
  selectText(editorBehind(wrapper, testId), needle, 0, needle.length);
}

function bodyOf(emitted: unknown[][] | undefined, index: number): NativeExamBodyParagraph[] {
  return emitted![index]!.find(Array.isArray) as NativeExamBodyParagraph[];
}

function boldOf(text: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: ["bold"], text, kept_gap_id: null }] }];
}

describe("ExamWorkspaceQuestionEditor shared rich-text target", () => {
  it("bolds the second option only after the caret was in the question and the first option", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, QUESTION, "Question");
    selectIn(wrapper, OPTION_1, "Option");
    selectIn(wrapper, OPTION_2, "Other");

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toEqual([["item_001", "choice_002", boldOf("Other"), true]]);
    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });

  it("follows focus back from an option to the question text", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, OPTION_1, "Option");
    selectIn(wrapper, QUESTION, "Question");

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    expect(wrapper.emitted("updateBody")).toHaveLength(1);
    expect(bodyOf(wrapper.emitted("updateBody"), 0)).toEqual(boldOf("Question"));
  });

  it("applies superscript, subscript and a heading to the focused option", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, QUESTION, "Question");
    selectIn(wrapper, OPTION_1, "Option");

    await wrapper.get(SUPERSCRIPT).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["superscript"], text: "Option", kept_gap_id: null },
    ]);

    await wrapper.get(SUBSCRIPT).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: ["subscript"], text: "Option", kept_gap_id: null },
    ]);

    await wrapper.get(HEADING_2).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 2)[0]!.heading_level).toBe(2);
    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });

  it("applies the toolbar to the focused Kategorisera entry", async () => {
    const wrapper = await mountEditor(buildMatchingItem());
    selectIn(wrapper, QUESTION, "Match each");
    selectIn(wrapper, MATCH_LEFT, "absence from school without permission");

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateBody")).toBeUndefined();
    expect(wrapper.emitted("updateMatchEntryBody")).toEqual([
      ["item_001", "left", "left_001", boldOf("absence from school without permission"), true],
    ]);
  });

  it("never edits the previous item's option after the editor shows another item", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, OPTION_1, "Option");

    // The pane reuses this editor for the next item; its choices repeat the ids
    // and the text, so nothing but the item changes under the old selection.
    const next = buildChoiceWithText();
    next.item_id = "item_002";
    await wrapper.setProps({ item: next });
    await settleEditors();

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });

  it("never edits an option that was removed while it had focus", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, OPTION_2, "Other");

    const shorter = buildChoiceWithText();
    shorter.choices = shorter.choices.slice(0, 1);
    await wrapper.setProps({ item: shorter });

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
  });

  it("edits the option again when the teacher returns to it after another item", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, OPTION_1, "Option");
    const next = buildChoiceWithText();
    next.item_id = "item_002";
    await wrapper.setProps({ item: next });
    await settleEditors();

    selectIn(wrapper, OPTION_2, "Other");
    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toEqual([["item_002", "choice_002", boldOf("Other"), true]]);
  });

  it("keeps toggling the same option across repeated toolbar clicks", async () => {
    const wrapper = await mountEditor(buildChoiceWithText());
    selectIn(wrapper, OPTION_1, "Option");

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Option", kept_gap_id: null },
    ]);

    // The owner stores the emitted body and passes it back; the selection stays.
    const echoed = buildChoiceWithText();
    echoed.choices[0]!.body = bodyOf(wrapper.emitted("updateChoiceBody"), 0);
    await wrapper.setProps({ item: echoed });

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: [], text: "Option", kept_gap_id: null },
    ]);
  });

  it("keeps the toolbar and its glyphs silent while the editor is locked", async () => {
    const wrapper = await mountEditor(buildChoiceWithText(), true);
    selectIn(wrapper, OPTION_1, "Option");

    expect(wrapper.get(BOLD).attributes("disabled")).toBeDefined();
    expect(wrapper.get(HEADING_2).attributes("disabled")).toBeDefined();
    await wrapper.get(BOLD).trigger("click");
    await wrapper.get(SUPERSCRIPT).trigger("click");
    await wrapper.get(HEADING_2).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    expect(wrapper.emitted("updateBody")).toBeUndefined();
  });
});
