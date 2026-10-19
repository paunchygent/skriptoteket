/**
 * Exam workspace gap tool pointer geometry for specs.
 *
 * Domain purpose:
 *   jsdom has no layout, so the gap tool click path (which resolves the word
 *   under the pointer through `view.coordsAtPos` and `event.clientX`) needs
 *   a stubbed character grid plus a click dispatcher that carries a clientX
 *   inside the clicked word. Every gap tool click spec shares this fixed
 *   10px column grid so a pointer click lands on the same word the caret
 *   selection names, and a click with the pointer on a separator still only
 *   places the caret.
 *
 * Relationships:
 *   - Used by the gap tool click specs in this directory and by the
 *     walking-skeleton slice spec support.
 */

import type { Editor } from "@tiptap/core";
import { vi } from "vitest";

/** One stubbed character column, in pixels. */
export const GAP_POINTER_CHAR_PX = 10;

/** The stubbed grid's left edge, in pixels. */
export const GAP_POINTER_ORIGIN_PX = 50;

/** Views already carrying the stubbed grid; the stub installs once per view. */
const stubbedViews = new WeakSet<object>();

/**
 * jsdom has no layout: every document position gets a fixed 10px column, so
 * a clientX inside one column tells exactly which character the pointer hit.
 * Installing twice on the same view keeps the first stub.
 */
export function stubLinearGapPointerGeometry(editor: Editor): void {
  if (stubbedViews.has(editor.view)) {
    return;
  }
  stubbedViews.add(editor.view);
  vi.spyOn(editor.view, "coordsAtPos").mockImplementation((pos: number) => {
    const left = GAP_POINTER_ORIGIN_PX + pos * GAP_POINTER_CHAR_PX;
    return { left, right: left, top: 60, bottom: 74 };
  });
}

/** The horizontal middle of the character starting at `charPos`. */
export function gapPointerMiddle(charPos: number): number {
  return GAP_POINTER_ORIGIN_PX + charPos * GAP_POINTER_CHAR_PX + GAP_POINTER_CHAR_PX / 2;
}

/**
 * A primary click at `pos` with the pointer at `clientX`; returns whether a
 * handler consumed it, as the gap tool's word check reads both.
 */
export function dispatchGapToolClick(editor: Editor, pos: number, clientX: number): unknown {
  let result: unknown;
  editor.view.someProp("handleClick", (handler) => {
    result = handler(
      editor.view,
      pos,
      new MouseEvent("click", { bubbles: true, cancelable: true, clientX }),
    );
    return result;
  });
  return result;
}
