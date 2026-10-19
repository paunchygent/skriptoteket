/**
 * Exam workspace rich-text editor: the floating gap button keyboard route.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 Q13, amending Q12):
 *   While the button shows, Tab in the editor moves focus to it and it stays
 *   shown; Enter or Space (the native button activation) converts the stored
 *   word; Escape hides it and returns focus to the editor with the caret
 *   where it was; Shift+Tab returns focus to the editor and keeps it shown;
 *   Tab from it moves focus to the next focusable element after the editor
 *   and hides it; focus leaving it for anything else hides it, while a
 *   focusout back into the editor keeps it.
 *
 * jsdom has no layout, so clicks reach the view through
 * `someProp("handleClick")`, keydown in the editor through
 * `someProp("handleKeyDown")`, and keydown/focusout on the button through
 * synthetic DOM events; coordinates are stubbed. Enter and Space rely on the
 * native button activation, which jsdom does not synthesize, so those tests
 * dispatch the key (asserting the button takes no key handling of its own)
 * and then click, as a browser would. The button teleports to
 * document.body, so it is found through `document` rather than the wrapper.
 */

import { Editor } from "@tiptap/core";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { paragraph, posIn, releaseEditor, text } from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { wordRangeAtDocPosition } from "./examWorkspaceGapWord";

type Body = NativeExamBodyParagraph[];
type Creation = [Body, string, string];

type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  surface: HTMLElement;
  before: HTMLInputElement;
  after: HTMLButtonElement;
  updates: Array<[Body, boolean]>;
  creations: Creation[];
};

const openedWrappers: VueWrapper[] = [];

/** Mount the editor between a focusable input and a focusable button. */
async function openKeyboardEditor(): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const creations: Creation[] = [];
  const keys: ExamWorkspaceHistoryKeys = { undo: vi.fn(), redo: vi.fn() };
  const Host = defineComponent({
    setup() {
      provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys);
      return () =>
        h("div", [
          h("input", { "data-test": "keyboard-before" }),
          h(ExamWorkspaceRichTextEditor, {
            label: "Frågetext",
            testId: "editor-under-test",
            body: [paragraph(text("Huvudstaden är Paris."))],
            gapsInteractive: true,
            nextGapId: "gap_002",
            onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
            onCreateGap: (body: Body, gapId: string, seed: string) => creations.push([body, gapId, seed]),
          }),
          h("button", { "data-test": "keyboard-after", type: "button" }, "Efter"),
        ]);
    },
  });
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  const candidate = wrapper.get("[data-test='editor-under-test']").element;
  if (!(candidate instanceof HTMLElement) || !("editor" in candidate)) {
    throw new Error("the editor did not mount");
  }
  const attached = candidate.editor;
  if (!(attached instanceof Editor)) {
    throw new Error("the editor did not mount");
  }
  const before = wrapper.get("[data-test='keyboard-before']").element;
  const after = wrapper.get("[data-test='keyboard-after']").element;
  if (!(before instanceof HTMLInputElement) || !(after instanceof HTMLButtonElement)) {
    throw new Error("the keyboard neighbours did not mount");
  }
  openedWrappers.push(wrapper);
  return { wrapper, editor: attached, surface: candidate, before, after, updates, creations };
}

/** A primary click at `pos`, as a mousedown would leave it behind. */
function clickAt(opened: Opened, pos: number): void {
  opened.editor.view.someProp("handleClick", (handler) =>
    handler(opened.editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true })),
  );
}

/** A keydown in the editor surface, as ProseMirror would receive it. */
function keyDownInEditor(opened: Opened, init: KeyboardEventInit): void {
  opened.editor.view.someProp("handleKeyDown", (handler) =>
    handler(opened.editor.view, new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init })),
  );
}

/** TipTap focuses the editor on the next animation frame; flush it in jsdom. */
function flushEditorFocus(): Promise<void> {
  return new Promise<void>((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

/** The floating button teleports to `document.body`, outside the wrapper. */
function gapButton(): HTMLButtonElement | null {
  const candidate = document.body.querySelector("[data-test='exam-workspace-make-gap']");
  return candidate instanceof HTMLButtonElement ? candidate : null;
}

function shownGapButton(): HTMLButtonElement {
  const button = gapButton();
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error("the floating gap button did not open");
  }
  return button;
}

async function openWithButton(): Promise<Opened> {
  const opened = await openKeyboardEditor();
  opened.editor.view.dom.style.lineHeight = "32px";
  opened.editor.view.dom.style.fontSize = "16px";
  const rect = new DOMRect(50, 50, 40, 16);
  vi.spyOn(opened.editor.view, "coordsAtPos").mockReturnValue(rect);
  opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
  clickAt(opened, posIn(opened.editor, "Paris", 1));
  await nextTick();
  await nextTick();
  return opened;
}

describe("ExamWorkspaceRichTextEditor makeGapButton keyboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    while (openedWrappers.length > 0) {
      openedWrappers.pop()?.unmount();
    }
    releaseEditor();
  });

  it("Tab in the editor focuses the button and it stays shown", async () => {
    const opened = await openWithButton();
    expect(gapButton()).not.toBeNull();

    keyDownInEditor(opened, { key: "Tab" });
    await nextTick();

    const button = shownGapButton();
    expect(document.activeElement).toBe(button);
  });

  it("Enter converts the stored word through the native button activation", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await nextTick();
    expect(gapButton()).not.toBeNull();

    button.click();
    await nextTick();
    expect(opened.creations).toHaveLength(1);
    expect(opened.creations[0]![2]).toBe("Paris");
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("Space converts the stored word through the native button activation", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
    await nextTick();
    expect(gapButton()).not.toBeNull();

    button.click();
    await nextTick();
    expect(opened.creations).toHaveLength(1);
    expect(opened.creations[0]![2]).toBe("Paris");
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("Escape hides the button and returns focus to the editor with the caret in the word", async () => {
    const opened = await openWithButton();
    const clickPos = posIn(opened.editor, "Paris", 1);
    const word = wordRangeAtDocPosition(opened.editor.state.doc, clickPos);
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    await flushEditorFocus();

    expect(gapButton()).toBeNull();
    expect(document.activeElement).toBe(opened.editor.view.dom);
    const head = opened.editor.state.selection.head;
    expect(word).not.toBeNull();
    expect(head).toBeGreaterThanOrEqual(word!.from);
    expect(head).toBeLessThanOrEqual(word!.to);
  });

  it("Shift+Tab on the button focuses the editor and keeps it shown", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }));
    await nextTick();
    await flushEditorFocus();

    expect(document.activeElement).toBe(opened.editor.view.dom);
    expect(gapButton()).not.toBeNull();
  });

  it("Tab on the button focuses the next element after the editor and hides it", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    await nextTick();

    expect(document.activeElement).toBe(opened.after);
    expect(gapButton()).toBeNull();
  });

  it("focus moving to an input before the editor hides it", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: opened.before }));
    await nextTick();

    expect(gapButton()).toBeNull();
  });

  it("a focusout back into the editor keeps it shown", async () => {
    const opened = await openWithButton();
    const button = shownGapButton();
    button.focus();

    button.dispatchEvent(
      new FocusEvent("focusout", { bubbles: true, relatedTarget: opened.editor.view.dom }),
    );
    await nextTick();

    expect(gapButton()).not.toBeNull();
  });

  it("an editor blur into the button keeps it shown", async () => {
    const opened = await openWithButton();
    opened.surface.focus();
    expect(gapButton()).not.toBeNull();

    keyDownInEditor(opened, { key: "Tab" });
    await nextTick();
    await nextTick();

    expect(gapButton()).not.toBeNull();
    expect(document.activeElement).toBe(gapButton());
  });
});
