/**
 * Gap tool shortcut on macOS.
 *
 * Domain purpose:
 *   Cmd+Option+G toggles the gap tool through the `onToggleGapTool` option,
 *   whether the key arrives as "g" or as the Option-modified "©", while
 *   Ctrl+Option+G does nothing. Keys are real `keydown` events dispatched on
 *   the editor DOM and handled by the keymaps.
 *
 * Relationships:
 *   - `examWorkspaceRichTextSchema` owns the `gapToolKeys` extension under test.
 *   - The keymap reads the platform once, when ProseMirror's keymap module
 *     loads, so the Mac is reported before any import runs.
 */
import { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";

vi.hoisted(() => {
  Object.defineProperty(window.navigator, "platform", { value: "MacIntel", configurable: true });
});

const editors: Editor[] = [];
afterEach(() => {
  while (editors.length) {
    editors.pop()?.destroy();
  }
  document.body.innerHTML = "";
});

function openEditor(onToggleGapTool: () => boolean): Editor {
  const editor = new Editor({
    extensions: examRichTextExtensions({
      gapState: () => ({ label: "Lucka", accessibleLabel: "Lucka", empty: true }),
      pictureUrl: () => undefined,
      keptGapToolOn: () => false,
      onUndo: () => undefined,
      onRedo: () => undefined,
      onToggleGapTool,
    }),
    content: {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "hello" }] }],
    },
  });
  editors.push(editor);
  return editor;
}

function dispatchKey(
  editor: Editor,
  key: string,
  modifiers: { altKey?: boolean; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean } = {},
  keyCode?: number,
): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...modifiers });
  if (keyCode !== undefined) {
    Object.defineProperty(event, "keyCode", { value: keyCode });
    Object.defineProperty(event, "which", { value: keyCode });
  }
  editor.view.dom.dispatchEvent(event);
  return event;
}

describe("gap tool shortcut on macOS", () => {
  it.each([["g"], ["©"]])(
    "calls onToggleGapTool once for Cmd+Option+G arriving as %s",
    (key) => {
      const onToggleGapTool = vi.fn(() => true);
      const editor = openEditor(onToggleGapTool);
      const event = dispatchKey(editor, key, { metaKey: true, altKey: true }, 71);
      expect(onToggleGapTool).toHaveBeenCalledTimes(1);
      expect(event.defaultPrevented).toBe(true);
      expect(editor.getText()).toBe("hello");
    },
  );

  it("does not call onToggleGapTool for Ctrl+Option+G", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "g", { ctrlKey: true, altKey: true }, 71);
    expect(onToggleGapTool).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
    expect(editor.getText()).toBe("hello");
  });
});
