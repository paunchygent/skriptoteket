/**
 * Exam workspace gap tool pointer geometry for specs.
 *
 * Domain purpose:
 *   jsdom has no layout, so the gap tool click path (which resolves the word
 *   under the pointer through `view.coordsAtPos` and `event.clientX`) needs
 *   a stubbed character grid plus a click dispatcher that carries a clientX
 *   inside the clicked word. Every gap tool click spec shares a fixed 10px
 *   column grid so a pointer click lands on the same word the caret
 *   selection names, and a click with the pointer on a separator still only
 *   places the caret. The linear grid grows right per document position; the
 *   decreasing grid grows left, modelling a right-to-left run where a
 *   character's start caret sits right of its end caret.
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

/** Views already carrying the stubbed `posAtCoords`; the stub installs once per view. */
const stubbedPositions = new WeakSet<object>();

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
 * jsdom has no layout: a right-to-left character grid where every next
 * document position sits one 10px column further left, so the start caret of
 * a character is right of its end caret on screen. Installing twice on the
 * same view keeps the first stub.
 */
export function stubDecreasingGapPointerGeometry(editor: Editor): void {
  if (stubbedViews.has(editor.view)) {
    return;
  }
  stubbedViews.add(editor.view);
  vi.spyOn(editor.view, "coordsAtPos").mockImplementation((pos: number) => {
    const left = GAP_POINTER_ORIGIN_PX - pos * GAP_POINTER_CHAR_PX;
    return { left, right: left, top: 60, bottom: 74 };
  });
}

/** The horizontal middle of the character starting at `charPos` in the decreasing grid. */
export function gapPointerMiddleDecreasing(charPos: number): number {
  return GAP_POINTER_ORIGIN_PX - charPos * GAP_POINTER_CHAR_PX - GAP_POINTER_CHAR_PX / 2;
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

/**
 * jsdom has no layout, so ProseMirror's `posAtCoords` (which reads the DOM
 * through `caretRangeFromPoint`) finds nothing: stub it with the inverse of
 * the linear character grid, so a real DOM `mousedown` resolves to the same
 * document position a real browser would report for that `clientX`. The
 * floor keeps clicks inside a character on that character's start boundary,
 * which the click path checks first. Installing twice on the same view
 * keeps the first stub.
 */
export function stubLinearGapPointerPositions(editor: Editor): void {
  if (stubbedPositions.has(editor.view)) {
    return;
  }
  stubbedPositions.add(editor.view);
  stubLinearGapPointerGeometry(editor);
  vi.spyOn(editor.view, "posAtCoords").mockImplementation((coords: { left: number; top: number }) => {
    const size = editor.view.state.doc.content.size;
    const pos = Math.min(Math.max(Math.floor((coords.left - GAP_POINTER_ORIGIN_PX) / GAP_POINTER_CHAR_PX), 0), size);
    return { pos, inside: pos };
  });
}

/**
 * A real DOM press pair through ProseMirror's own mouse handling (its
 * single/double click classification included), as a real browser routes a
 * click: `mousedown` with the press count, then `mouseup` with the same
 * count. Returns after the pair dispatched; the caller settles the tool's
 * deferred release check. Needs `stubLinearGapPointerPositions`.
 */
export function pressGapToolClick(editor: Editor, surface: HTMLElement, clientX: number, detail: number): void {
  surface.dispatchEvent(
    new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX, detail }),
  );
  surface.dispatchEvent(
    new MouseEvent("mouseup", { bubbles: true, cancelable: true, button: 0, clientX, detail }),
  );
}
