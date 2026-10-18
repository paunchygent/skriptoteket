/**
 * Rich-text entry editing helpers for exam workspace specs.
 *
 * Purpose:
 *   jsdom has no layout, so a real pointer cannot place a selection. Specs
 *   place selections through TipTap commands and dispatch real `keydown`
 *   events on the editing surface, which ProseMirror's keymaps handle. A
 *   typed character is inserted with `insertContent`, because the browser —
 *   not ProseMirror — inserts a typed character from a keydown. The editors
 *   mount on the tick after their component, so `settleEditors` waits for it.
 */

import type { Editor } from "@tiptap/core";
import type { VueWrapper } from "@vue/test-utils";
import { nextTick } from "vue";

type Surface = HTMLElement & { editor?: Editor };

/** Wait until every mounted TipTap editor has created its editing surface. */
export async function settleEditors(): Promise<void> {
  await nextTick();
  await nextTick();
}

/** The editor behind the editing surface carrying `data-test` `testId`. */
export function editorBehind(wrapper: VueWrapper, testId: string): Editor {
  const surface = wrapper.get(`[data-test="${testId}"]`).element as Surface;
  if (!surface.editor) {
    throw new Error(`no editor behind ${testId}`);
  }
  return surface.editor;
}

export function surfaceOf(wrapper: VueWrapper, testId: string): HTMLElement {
  return wrapper.get(`[data-test="${testId}"]`).element as HTMLElement;
}

/** Position `offset` characters into the first text node that contains `needle`. */
export function posIn(editor: Editor, needle: string, offset: number): number {
  let found = -1;
  editor.state.doc.descendants((node, pos) => {
    if (found < 0 && node.isText && node.text?.includes(needle)) {
      found = pos + (node.text.indexOf(needle) + offset);
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no text "${needle}"`);
  }
  return found;
}

/** Select the first `needle` text from `from` to `to` characters into it. */
export function selectText(editor: Editor, needle: string, from: number, to: number): void {
  editor.commands.setTextSelection({ from: posIn(editor, needle, from), to: posIn(editor, needle, to) });
}

export function press(
  surface: HTMLElement,
  key: string,
  modifiers: { shiftKey?: boolean; ctrlKey?: boolean; metaKey?: boolean } = {},
): KeyboardEvent {
  // ProseMirror's own delete handling reads `keyCode`, as every browser sets it.
  const keyCode = { Backspace: 8, Enter: 13, Delete: 46 }[key];
  const event = new KeyboardEvent("keydown", { key, keyCode, bubbles: true, cancelable: true, ...modifiers });
  surface.dispatchEvent(event);
  return event;
}
