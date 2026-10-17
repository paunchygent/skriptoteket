/**
 * Exam workspace question editor, shared rich-text formatting target.
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
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { choiceItem } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { plainBody } from "./examWorkspaceRichText";

function mountEditor(item: NativeExamItem, disabled = false) {
  return mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
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

/** Select a character range inside one surface's first text node, like a drag. */
function selectTextRange(element: HTMLElement, start: number, end: number): void {
  const node = document.createTreeWalker(element, NodeFilter.SHOW_TEXT).nextNode();
  if (!node) {
    throw new Error("rich surface has no text node");
  }
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
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

describe("ExamWorkspaceQuestionEditor shared rich-text target", () => {
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

  it("releases the previous item's saved option selection when the native item is replaced", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    const next = buildChoiceWithText();
    next.item_id = "item_002";
    next.choices[0]!.body = plainBody("New option");
    await wrapper.setProps({ item: next });

    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    wrapper.unmount();
  });

  it("releases a saved option selection when a replacement item repeats the same entry text", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    const sameText = buildChoiceWithText();
    sameText.item_id = "item_002";
    await wrapper.setProps({ item: sameText });

    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("releases a saved option selection when the same item's option body is replaced", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    const replaced = buildChoiceWithText();
    replaced.choices[0]!.body = plainBody("Replaced option");
    await wrapper.setProps({ item: replaced });

    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("releases a saved matching entry when the matching item is replaced with the same entry ids", async () => {
    const wrapper = mountEditor(buildMatchingItem());
    const entry = wrapper.get(MATCH_LEFT);

    await entry.trigger("focus");
    selectSurface(entry.element as HTMLElement);

    const base = buildMatchingItem();
    const next = buildMatchingItem({
      item_id: "item_002",
      match_left: base.match_left.map((left) =>
        left.left_id === "left_001" ? { ...left, body: plainBody("another row") } : left,
      ),
    });
    await wrapper.setProps({ item: next });

    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");

    expect(wrapper.emitted("updateMatchEntryBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps every glyph off a stale question when the browser range crosses rich surfaces", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const question = wrapper.get(QUESTION);
    const option = wrapper.get(OPTION);

    await question.trigger("focus");
    selectSurface(question.element as HTMLElement);

    const questionText = document
      .createTreeWalker(question.element, NodeFilter.SHOW_TEXT)
      .nextNode()!;
    const optionText = document.createTreeWalker(option.element, NodeFilter.SHOW_TEXT).nextNode()!;
    const range = document.createRange();
    range.setStart(questionText, 0);
    range.setEnd(optionText, 3);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");
    await wrapper.get(HEADING_2).trigger("click");

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(wrapper.emitted("updateParagraphHeading")).toBeUndefined();
    expect(wrapper.emitted("updateChoiceBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps the same option selection across repeated toggles while the toolbar holds focus", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectSurface(option.element as HTMLElement);

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Option" },
    ]);

    // The browser drops the range while the toolbar button holds focus; the
    // saved paragraph offsets must keep the same surface for the next toggle.
    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: [], text: "Option" },
    ]);
    wrapper.unmount();
  });

  it("keeps a split-run saved selection when the emitted body echoes back as props", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectTextRange(option.element as HTMLElement, 0, 2);

    await wrapper.get(BOLD).trigger("click");
    const marked = bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!;
    expect(marked.segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Op" },
      { kind: "text", marks: [], text: "tion" },
    ]);

    // The document stores the body exactly as the toggle emitted it.
    const echoed = buildChoiceWithText();
    echoed.choices[0]!.body = [marked];
    await wrapper.setProps({ item: echoed });

    // The browser drops the range while the toolbar button holds focus; the
    // saved offsets must survive the split run and still cover "Op".
    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: [], text: "Option" },
    ]);
    wrapper.unmount();
  });

  it("keeps a saved selection when a mark-only update merges the split run back", async () => {
    const wrapper = mountEditor(buildChoiceWithText());
    const option = wrapper.get(OPTION);

    await option.trigger("focus");
    selectTextRange(option.element as HTMLElement, 0, 2);
    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 0)[0]!.segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Op" },
      { kind: "text", marks: [], text: "tion" },
    ]);

    // The owner normalizes the mark-split run back into one text run; only
    // run boundaries changed, so the saved offsets must survive.
    const merged = buildChoiceWithText();
    merged.choices[0]!.body = [
      { heading_level: null, segments: [{ kind: "text", marks: ["bold"], text: "Option" }] },
    ];
    await wrapper.setProps({ item: merged });

    window.getSelection()!.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    await wrapper.get(BOLD).trigger("click");
    expect(bodyOf(wrapper.emitted("updateChoiceBody"), 1)[0]!.segments).toEqual([
      { kind: "text", marks: [], text: "Op" },
      { kind: "text", marks: ["bold"], text: "tion" },
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
