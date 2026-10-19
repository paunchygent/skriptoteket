/**
 * Exam workspace rich-text editor: the gap tool click path.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 G1):
 *   With the `gapTool` prop on, a primary click inside a word turns that word
 *   into a gap at once (one `createGap`, never `update`, no floating button),
 *   and a drag selection inside one paragraph turns into one gap on mouseup.
 *   A click on a space only places the caret, a click on a gap chip still
 *   opens it (`activateGap`), typing still emits `update`, and with the prop
 *   off a word click shows the floating button exactly as before.
 *
 * jsdom has no layout, so selections are set through TipTap commands, clicks
 * reach the view through `someProp("handleClick")`, a drag release is a real
 * `mouseup` event on the surface (the tool reads the finished selection on
 * the next tick), and coordinates are stubbed where the button is asserted.
 * The button teleports to document.body, so it is found through `document`.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { Editor } from "@tiptap/core";
import { defineComponent, h, nextTick, reactive } from "vue";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import {
  atomPos,
  gap,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import type { ExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";

type Body = NativeExamBodyParagraph[];
type Creation = [Body, string, string];

type Opened = {
  wrapper: VueWrapper;
  editor: Editor;
  surface: HTMLElement;
  updates: Array<[Body, boolean]>;
  creations: Creation[];
  activations: Array<[string, HTMLElement]>;
  toggles: string[];
  escapes: string[];
  setProps: (props: Partial<EditorProps>) => Promise<void>;
};

type EditorProps = {
  body: Body;
  gapsInteractive?: boolean;
  disabled?: boolean;
  nextGapId?: string | null;
  gapTool?: boolean;
};

const openedWrappers: VueWrapper[] = [];

async function openEditor(initial: EditorProps): Promise<Opened> {
  const updates: Array<[Body, boolean]> = [];
  const creations: Creation[] = [];
  const activations: Array<[string, HTMLElement]> = [];
  const toggles: string[] = [];
  const escapes: string[] = [];
  const keys: ExamWorkspaceHistoryKeys = { undo: vi.fn(), redo: vi.fn() };
  const live = reactive<EditorProps>({ ...initial });
  const Host = defineComponent({
    setup() {
      provideRichTextTargetRegistry();
      provideExamWorkspaceHistoryKeys(keys);
      return () =>
        h(ExamWorkspaceRichTextEditor, {
          label: "Frågetext",
          testId: "editor-under-test",
          body: live.body,
          gapsInteractive: live.gapsInteractive,
          disabled: live.disabled,
          nextGapId: live.nextGapId,
          gapTool: live.gapTool,
          onUpdate: (body: Body, structural: boolean) => updates.push([body, structural]),
          onCreateGap: (body: Body, gapId: string, seed: string) => creations.push([body, gapId, seed]),
          onActivateGap: (gapId: string, element: HTMLElement) => activations.push([gapId, element]),
          onToggleGapTool: () => toggles.push("toggle"),
          onEscape: () => escapes.push("escape"),
        });
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
  openedWrappers.push(wrapper);
  return {
    wrapper,
    editor: attached,
    surface: candidate,
    updates,
    creations,
    activations,
    toggles,
    escapes,
    setProps: async (props) => {
      Object.assign(live, props);
      await nextTick();
    },
  };
}

/** A primary click at `pos`; returns whether a handler consumed it. */
function clickAt(opened: Opened, pos: number): unknown {
  let result: unknown;
  opened.editor.view.someProp("handleClick", (handler) => {
    result = handler(opened.editor.view, pos, new MouseEvent("click", { bubbles: true, cancelable: true }));
    return result;
  });
  return result;
}

/** A drag release: a real mouseup on the surface, then the tool's next tick. */
async function releaseMouse(opened: Opened): Promise<void> {
  opened.surface.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
}

function stubGeometry(opened: Opened): void {
  const rect = new DOMRect(50, 60, 40, 14);
  vi.spyOn(opened.editor.view, "coordsAtPos").mockReturnValue(rect);
}

/** The floating button teleports to `document.body`, outside the wrapper. */
function gapButton(): HTMLElement | null {
  const candidate = document.body.querySelector("[data-test='exam-workspace-make-gap']");
  return candidate instanceof HTMLElement ? candidate : null;
}

describe("ExamWorkspaceRichTextEditor gap tool", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    while (openedWrappers.length > 0) {
      openedWrappers.pop()?.unmount();
    }
    releaseEditor();
  });

  it("turns the clicked word into a gap at once, with no floating button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    // The browser's mouseup runs before the click; the deferred release check
    // must not add a second gap after the click already converted the word.
    opened.surface.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true }));
    const handled = clickAt(opened, posIn(opened.editor, "world", 1));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(handled).toBe(true);
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("world");
    expect(body).toEqual([paragraph(text("hello "), gap("gap_002"))]);
    expect(gapButton()).toBeNull();
  });

  it("places only the caret on a space, with no gap and no button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world "))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const end = posIn(opened.editor, "hello world ", 12);
    opened.editor.commands.setTextSelection(end);
    const handled = clickAt(opened, end);
    await nextTick();

    expect(handled).toBeFalsy();
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("opens a clicked gap chip instead of making a new gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello "), gap("gap_001"), text(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const gapPos = atomPos(opened.editor, "examGap");
    const node = opened.editor.state.doc.nodeAt(gapPos);
    const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
      handler(opened.editor.view, gapPos, node!, gapPos, new MouseEvent("click"), true),
    );

    expect(handled).toBe(true);
    expect(opened.activations).toHaveLength(1);
    expect(opened.activations[0]![0]).toBe("gap_001");
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("turns a drag selection inside one paragraph into one gap on release", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "hello world", 0),
      to: posIn(opened.editor, "hello world", 11),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("hello world");
    expect(body).toEqual([paragraph(gap("gap_002"))]);
    expect(gapButton()).toBeNull();
  });

  it("makes no gap on release across two paragraphs", async () => {
    const opened = await openEditor({
      body: [paragraph(text("first")), paragraph(text("second"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "first", 2),
      to: posIn(opened.editor, "second", 3),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("first\n\nsecond");
  });

  it("makes no gap on release over a range containing a gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a"), gap("gap_001"), text("b"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "a", 0),
      to: posIn(opened.editor, "b", 1),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("ab");
  });

  it("emits update only while typing with the tool on", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 5));
    opened.editor.commands.insertContent("x");
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(1);
    expect(opened.editor.getText()).toBe("hello worldx");
  });

  it("shows the floating button, not a gap, on a word click with the tool off", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    const handled = clickAt(opened, posIn(opened.editor, "world", 1));
    await nextTick();
    await nextTick();

    expect(handled).toBeFalsy();
    expect(opened.creations).toHaveLength(0);
    expect(gapButton()).not.toBeNull();
  });

  it("removes a shown floating button when the tool turns on", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    clickAt(opened, posIn(opened.editor, "world", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    await opened.setProps({ gapTool: true });

    expect(gapButton()).toBeNull();
    expect(opened.creations).toHaveLength(0);
  });

  it("creates nothing on a word click with the tool on but no next gap id", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: null,
      gapTool: true,
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    const handled = clickAt(opened, posIn(opened.editor, "world", 1));
    await releaseMouse(opened);

    expect(handled).toBeFalsy();
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });
});

describe("ExamWorkspaceRichTextEditor gap tool wiring", () => {
  /** Ctrl+Alt+G as ProseMirror's keymap reads it: the key code comes from `keyCode`, as browsers set it. */
  function dispatchGapShortcut(
    wired: Opened,
    key: string,
    modifiers: { altKey?: boolean; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean } = {},
  ): KeyboardEvent {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...modifiers });
    Object.defineProperty(event, "keyCode", { value: 71 });
    Object.defineProperty(event, "which", { value: 71 });
    wired.surface.dispatchEvent(event);
    return event;
  }

  function pressEscape(wired: Opened): void {
    wired.surface.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }),
    );
  }

  it("emits toggleGapTool on Ctrl+Alt+G while gaps are interactive", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });

    const event = dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });

    expect(wired.toggles).toHaveLength(1);
    expect(wired.escapes).toHaveLength(0);
    expect(event.defaultPrevented).toBe(true);
    expect(wired.editor.getText()).toBe("hello world");
  });

  it("does not emit toggleGapTool while gaps are not interactive or while disabled", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: false,
      nextGapId: "gap_002",
    });

    dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });
    expect(wired.toggles).toHaveLength(0);

    await wired.setProps({ gapsInteractive: true, disabled: true });
    const event = dispatchGapShortcut(wired, "g", { ctrlKey: true, altKey: true });
    expect(wired.toggles).toHaveLength(0);
    expect(event.defaultPrevented).toBe(false);
  });

  it("emits escape on Escape, after the floating button takes its own Escape", async () => {
    const wired = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(wired);
    wired.editor.commands.setTextSelection(posIn(wired.editor, "world", 1));
    clickAt(wired, posIn(wired.editor, "world", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    pressEscape(wired);
    await nextTick();
    expect(gapButton()).toBeNull();
    expect(wired.escapes).toHaveLength(0);

    pressEscape(wired);
    await nextTick();
    expect(wired.escapes).toHaveLength(1);
    expect(wired.toggles).toHaveLength(0);
  });
});
