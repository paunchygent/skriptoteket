/**
 * Exam workspace item editor, shared rich-text formatting target.
 *
 * Expected behavior:
 *   The item editor has one formatting toolbar and one active rich target:
 *   the question paragraph, choice option or Kategorisera entry that owns
 *   the current selection. Moving the selection from the question text to
 *   an option and pressing a glyph edits the option and never the stale
 *   question selection. Superscript, subscript and heading glyphs reach the
 *   selected entry, and a locked editor emits nothing.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { plainBody } from "./examWorkspaceRichText";

function mountEditor(item: NativeExamItem, disabled = false) {
  return mount(ExamWorkspaceItemEditor, {
    attachTo: document.body,
    props: {
      attentionCount: 0,
      detailsOpen: false,
      disabled,
      item,
      position: 1,
      showNavigation: false,
      total: 1,
    },
  });
}

/** Select one surface's whole text and report it like a real selection change. */
function selectSurface(element: HTMLElement): void {
  const node = document.createTreeWalker(element, NodeFilter.SHOW_TEXT).nextNode();
  if (!node) {
    throw new Error("rich surface has no text node");
  }
  const range = document.createRange();
  range.selectNodeContents(node);
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  document.dispatchEvent(new Event("selectionchange"));
}

const QUESTION = '[data-test="exam-workspace-body-paragraph-0"]';
const OPTION = '[data-test="exam-workspace-choice-text-choice_001"]';
const MATCH_LEFT = '[data-test="exam-workspace-match-left-text-left_001"]';
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

function bodyOf(emitted: unknown[][] | undefined, index: number): NativeExamBodyParagraph[] {
  return emitted![index]![2] as NativeExamBodyParagraph[];
}

describe("ExamWorkspaceItemEditor shared rich-text target", () => {
  it("edits the selected option instead of the stale question selection", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const question = wrapper.get(QUESTION);
    const option = wrapper.get(OPTION);

    await question.trigger("focus");
    selectSurface(question.element as HTMLElement);
    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(wrapper.emitted("updateChoiceBody")).toEqual([
      [
        "item_001",
        "choice_001",
        [
          {
            heading_level: null,
            segments: [{ kind: "text", marks: ["bold"], text: "Option" }],
          },
        ],
      ],
    ]);
    wrapper.unmount();
  });

  it("switches to the option from the selection report alone, without focusing it", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const question = wrapper.get(QUESTION);
    const option = wrapper.get(OPTION);

    await question.trigger("focus");
    selectSurface(question.element as HTMLElement);
    // The browser reports the new selection without a focus event on the option.
    selectSurface(option.element as HTMLElement);

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Option" },
    ]);
    wrapper.unmount();
  });

  it("applies superscript, subscript and a heading to the selected option", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const question = wrapper.get(QUESTION);
    const option = wrapper.get(OPTION);

    await question.trigger("focus");
    selectSurface(question.element as HTMLElement);
    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    await wrapper.get(SUPERSCRIPT).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["superscript"], text: "Option" },
    ]);

    await wrapper.get(SUBSCRIPT).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: ["subscript"], text: "Option" },
    ]);

    await wrapper.get(HEADING_2).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 2)[0]!.heading_level).toBe(2);
    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    wrapper.unmount();
  });

  it("applies the toolbar to the selected Kategorisera entry", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const question = wrapper.get(QUESTION);
    const entry = wrapper.get(MATCH_LEFT);

    await question.trigger("focus");
    selectSurface(question.element as HTMLElement);
    // The selection report alone moves the active target to the matching entry.
    selectSurface(entry.element as HTMLElement);

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(wrapper.emitted("updateMatchEntryBody")).toEqual([
      [
        "item_001",
        "left",
        "left_001",
        [
          {
            heading_level: null,
            segments: [
              { kind: "text", marks: ["bold"], text: "absence from school without permission" },
            ],
          },
        ],
      ],
    ]);
    wrapper.unmount();
  });

  it("keeps the toolbar and its glyphs silent while the editor is locked", async () => {
    const wrapper = mountEditor(buildChoiceWithText(), true);
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    expect(wrapper.get(BOLD).attributes("disabled")).toBeDefined();
    expect(wrapper.get(HEADING_2).attributes("disabled")).toBeDefined();
    await wrapper.get(BOLD).trigger("click");
    await wrapper.get(SUPERSCRIPT).trigger("click");
    await wrapper.get(HEADING_2).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    wrapper.unmount();
  });
});
