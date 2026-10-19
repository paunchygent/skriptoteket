/**
 * Gap tool shortcut on a Windows Swedish layout.
 *
 * Domain purpose:
 *   Ctrl+Alt+G still toggles the gap tool, including the Caps Lock
 *   uppercase form (key "G" with no Shift), while a Swedish AltGr+2
 *   keypress (key "@") and an AltGr+G layout character (key "ŋ") never
 *   reach the toggle even though they carry Ctrl+Alt: ProseMirror skips
 *   its key-code fallback for Ctrl+Alt on Windows, so the key is left
 *   alone and the paragraph is not turned into a heading. Keys are real
 *   `keydown` events dispatched on the editor DOM.
 *
 * Relationships:
 *   - `examWorkspaceRichTextSchema` owns the `gapToolKeys` extension under test.
 *   - The keymap reads the platform once, when ProseMirror's keymap module
 *     loads, so the platform is reported before any import runs.
 */
import { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";

vi.hoisted(() => {
  Object.defineProperty(window.navigator, "platform", { value: "Win32", configurable: true });
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

describe("gap tool shortcut on Windows with a Swedish layout", () => {
  it("calls onToggleGapTool once for Ctrl+Alt+G and swallows the key", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "g", { ctrlKey: true, altKey: true }, 71);
    expect(onToggleGapTool).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("calls onToggleGapTool once for Caps Lock Ctrl+Alt+G and swallows the key", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "G", { ctrlKey: true, altKey: true, shiftKey: false }, 71);
    expect(onToggleGapTool).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("calls onToggleGapTool once for Shift+Ctrl+Alt+G", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "G", { ctrlKey: true, altKey: true, shiftKey: true }, 71);
    expect(onToggleGapTool).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("leaves a Swedish AltGr+2 alone: no toggle, no heading", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "@", { ctrlKey: true, altKey: true }, 50);
    expect(onToggleGapTool).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
    expect(editor.isActive("heading")).toBe(false);
    expect(editor.getJSON().content?.[0]?.type).toBe("paragraph");
    expect(editor.getText()).toBe("hello");
  });

  it("leaves an AltGr+G layout character alone: no toggle, no heading", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "ŋ", { ctrlKey: true, altKey: true }, 71);
    expect(onToggleGapTool).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
    expect(editor.isActive("heading")).toBe(false);
    expect(editor.getJSON().content?.[0]?.type).toBe("paragraph");
    expect(editor.getText()).toBe("hello");
  });
});
