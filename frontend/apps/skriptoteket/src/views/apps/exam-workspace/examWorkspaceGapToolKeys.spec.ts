/**
 * Gap tool shortcut on Windows and Linux.
 *
 * Domain purpose:
 *   Ctrl+Alt+G toggles the gap tool through the `onToggleGapTool` option, and
 *   the key is left alone when there is no gap tool (the callback returns
 *   false) or when a nearby key is pressed. Keys are real `keydown` events
 *   dispatched on the editor DOM and handled by the keymaps.
 *
 * Relationships:
 *   - `examWorkspaceRichTextSchema` owns the `gapToolKeys` extension under test.
 *   - `examWorkspaceGapToolKeys.windows.spec.ts` covers the Swedish AltGr
 *     layout where Ctrl+Alt doubles as AltGr.
 *   - `examWorkspaceGapToolKeys.mac.spec.ts` covers Cmd+Option+G on macOS.
 */
import { Editor } from "@tiptap/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";

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

describe("gap tool shortcut on Windows and Linux", () => {
  it("calls onToggleGapTool once for Ctrl+Alt+G and swallows the key", () => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "g", { ctrlKey: true, altKey: true }, 71);
    expect(onToggleGapTool).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
    expect(editor.getText()).toBe("hello");
  });

  it("leaves the key alone when the callback reports no gap tool", () => {
    const onToggleGapTool = vi.fn(() => false);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, "g", { ctrlKey: true, altKey: true }, 71);
    expect(onToggleGapTool).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(false);
    expect(editor.getText()).toBe("hello");
  });

  it.each([
    ["Ctrl+G", "g", { ctrlKey: true }],
    ["Ctrl+Shift+G", "G", { ctrlKey: true, shiftKey: true }],
    ["Alt+G", "g", { altKey: true }],
    ["plain g", "g", {}],
  ])("does not call onToggleGapTool for %s", (_name, key, modifiers) => {
    const onToggleGapTool = vi.fn(() => true);
    const editor = openEditor(onToggleGapTool);
    const event = dispatchKey(editor, key, modifiers, 71);
    expect(onToggleGapTool).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
    expect(editor.getText()).toBe("hello");
  });
});
