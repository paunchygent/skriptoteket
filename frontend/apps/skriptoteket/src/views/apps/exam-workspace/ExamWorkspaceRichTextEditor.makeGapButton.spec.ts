/**
 * Exam workspace rich-text editor: the floating gap button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 Q13, amending Q12: no text shift):
 *   A click inside a word shows a small glyph-only floating button
 *   ("Gör till lucka" tooltip and accessible name only, no border, fill or
 *   shadow) floating off the text in the line gap under the clicked word's
 *   end, covering no letters: a 24px-wide box, as tall as the letter-free
 *   band between the word's line and the next (line height minus font size),
 *   centred horizontally on the word end, left-clamped to the viewport. Only
 *   the glyph's own box takes clicks; the rest passes through to the text.
 *   Tab in the editor moves focus to the button while it stays shown; Enter
 *   or Space converts the stored word; Escape hides it and returns focus to
 *   the editor with the caret where it was; Shift+Tab returns focus to the
 *   editor and keeps it shown; Tab from it moves focus past the editor and
 *   hides it; focus leaving it anywhere else hides it. The button hides on
 *   any document change, on a caret move out of the word, on scroll or
 *   resize, and when the editor is disabled or has no next gap id.
 *
 * jsdom has no layout, so selections are set through TipTap commands and
 * clicks reach the view through `someProp("handleClick")`; coordinates are
 * stubbed where the placement is asserted. The button teleports to
 * document.body, so it is found through `document` rather than the wrapper.
 */

import { TextSelection } from "@tiptap/pm/state";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import {
  gap,
  paragraph,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  clickAt,
  gapButton,
  openEditor,
  releaseOpenedEditors,
  shownGapButton,
  stubGeometry,
} from "./ExamWorkspaceRichTextEditor.makeGap.specSupport";
import { ATOM_STATE_KEY } from "./examWorkspaceRichTextSchema";
import { ANCHORED_EDGE_PX } from "./useExamWorkspaceAnchoredPosition";
import { wordRangeAtDocPosition } from "./examWorkspaceGapWord";

/**
 * jsdom has no layout: `coordsAtPos` returns the word's text box for every
 * position. The surface carries inline `line-height: 32px` and
 * `font-size: 16px` (the unit proof numbers), so the letter-free band is
 * B = 32 - 16 = 16, the boundary between the word's line box and the next
 * is y0 = (50 + 66) / 2 + 32 / 2 = 74, and the button box is top = 74 - 8 =
 * 66, height 16, width 24, left = 90 - 12 = 78, horizontally centred on the
 * word end x = 90. It stays between the word's letters (bottom 66) and the
 * next line's letters (top 82) and covers no text.
 */
const WORD_BOX = { left: 50, top: 50, right: 90, bottom: 66 };

/** Give the surface the unit proof metrics: line height 32px, font 16px. */
function styleGapBand(opened: { editor: { view: { dom: HTMLElement } } }): void {
  opened.editor.view.dom.style.lineHeight = "32px";
  opened.editor.view.dom.style.fontSize = "16px";
}

describe("ExamWorkspaceRichTextEditor makeGap floating button", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseOpenedEditors();
    releaseEditor();
  });

  it("is glyph-only: no visible text, the name lives in the tooltip and aria-label only", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, WORD_BOX);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const button = shownGapButton();
    expect(button.textContent?.trim()).toBe("");
    expect(button.getAttribute("aria-label")).toBe("Gör till lucka");
    expect(button.getAttribute("title")).toBe("Gör till lucka");
    const classes = Array.from(button.classList);
    expect(classes.some((name) => name.startsWith("border-") || name.startsWith("bg-") || name.startsWith("shadow"))).toBe(false);
    expect(button.classList.contains("fixed")).toBe(true);
    expect(classes.some((name) => name.startsWith("focus-visible"))).toBe(true);
  });

  it("sits in the line gap under the clicked word's end and covers no letters", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    styleGapBand(opened);
    stubGeometry(opened, WORD_BOX);
    const clickPos = posIn(opened.editor, "Paris", 1);
    const word = wordRangeAtDocPosition(opened.editor.state.doc, clickPos);
    opened.editor.commands.setTextSelection(clickPos);
    clickAt(opened, clickPos);
    await nextTick();
    await nextTick();

    const calls = vi.mocked(opened.editor.view.coordsAtPos).mock.calls;
    expect(calls.some(([pos, side]) => pos === word?.to && side === -1)).toBe(true);
    const button = shownGapButton();
    expect(button.style.width).toBe("24px");
    expect(button.style.height).toBe("16px");
    const top = Number.parseFloat(button.style.top);
    const height = Number.parseFloat(button.style.height);
    expect(top).toBe(66);
    expect(top).toBeGreaterThanOrEqual(WORD_BOX.bottom);
    expect(top + height).toBeLessThanOrEqual(WORD_BOX.bottom + 16);
    const left = Number.parseFloat(button.style.left);
    const width = Number.parseFloat(button.style.width);
    expect(left + width / 2).toBe(WORD_BOX.right);
    expect(button.querySelector("svg")?.getAttribute("width")).toBe("14");
  });

  it("keeps the line-gap top with left clamped at the right viewport edge", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    styleGapBand(opened);
    stubGeometry(opened, WORD_BOX);
    vi.spyOn(window, "innerWidth", "get").mockReturnValue(100);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const button = shownGapButton();
    expect(button.style.left).toBe(`${100 - 24 - ANCHORED_EDGE_PX}px`);
    expect(button.style.top).toBe("66px");
    expect(button.style.height).toBe("16px");
  });

  it("passes a click on another word through to that word and converts nothing", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    styleGapBand(opened);
    const firstPos = posIn(opened.editor, "Paris", 1);
    const secondPos = posIn(opened.editor, "Huvudstaden", 0);
    const secondWord = wordRangeAtDocPosition(opened.editor.state.doc, secondPos);
    const firstBox = new DOMRect(50, 50, 40, 16);
    const secondBox = new DOMRect(150, 50, 40, 16);
    vi.spyOn(opened.editor.view, "coordsAtPos").mockImplementation((pos: number) =>
      pos === secondWord?.to ? secondBox : firstBox,
    );
    opened.editor.commands.setTextSelection(firstPos);
    clickAt(opened, firstPos);
    await nextTick();
    await nextTick();
    expect(shownGapButton().style.left).toBe("78px");

    clickAt(opened, secondPos);
    await nextTick();
    await nextTick();

    const button = shownGapButton();
    expect(button.style.left).toBe("178px");
    expect(button.style.top).toBe("66px");
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("shows in the line gap under the clicked word and converts it on click", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    styleGapBand(opened);
    stubGeometry(opened, WORD_BOX);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const button = gapButton();
    expect(button).not.toBeNull();
    expect(button?.textContent?.trim()).toBe("");
    expect(button?.getAttribute("aria-label")).toBe("Gör till lucka");
    expect(button?.getAttribute("title")).toBe("Gör till lucka");
    expect(button?.style.left).toBe("78px");
    expect(button?.style.top).toBe("66px");
    expect(button?.style.width).toBe("24px");
    expect(button?.style.height).toBe("16px");

    shownGapButton().click();
    await nextTick();
    expect(opened.creations).toHaveLength(1);
    expect(opened.creations[0]![2]).toBe("Paris");
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("converts the complete word across marks from a floating click", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Stock"), text("holm", ["bold"]), text("."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "holm", 2));
    clickAt(opened, posIn(opened.editor, "holm", 2));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    shownGapButton().click();
    await nextTick();
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Stockholm");
    expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
    expect(gapButton()).toBeNull();
  });

  it("sits in the line gap below the word even at the top of the viewport", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    styleGapBand(opened);
    stubGeometry(opened, { left: 50, top: 10, right: 90, bottom: 26 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    // y0 = (10 + 26) / 2 + 32 / 2 = 34, top = 34 - 8 = 26: below the word's
    // letters (bottom 26), never above the word however little room is above.
    const button = shownGapButton();
    expect(button.style.top).toBe("26px");
    expect(button.style.height).toBe("16px");
    expect(button.style.width).toBe("24px");
  });

  it("hides the button when the document changes", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    opened.editor.commands.insertContent("x");
    await nextTick();
    expect(gapButton()).toBeNull();
  });

  it("shows nothing without a next gap id or on a space", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).toBeNull();

    await opened.setProps({ nextGapId: "gap_002" });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris.", 6));
    expect(opened.editor.state.selection).toBeInstanceOf(TextSelection);
    clickAt(opened, posIn(opened.editor, "Paris.", 6));
    await nextTick();
    await nextTick();
    expect(gapButton()).toBeNull();
  });

  it("reads the clicked word from the click position, not the stale selection", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(1);
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 3));
    await nextTick();
    expect(gapButton()).not.toBeNull();
  });

  it("stays across a meta-only transaction that redraws the atoms", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    opened.editor.view.dispatch(opened.editor.state.tr.setMeta(ATOM_STATE_KEY, true));
    await nextTick();
    expect(gapButton()).not.toBeNull();
  });

  it("hides when the selection moves outside the word", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    opened.editor.commands.setTextSelection(posIn(opened.editor, "Huvudstaden", 0));
    await nextTick();
    expect(gapButton()).toBeNull();
  });

  it("converts the whole stored word when the caret moved inside it before confirming", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(1);
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 4));
    await nextTick();

    shownGapButton().click();
    await nextTick();
    expect(opened.creations).toHaveLength(1);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Paris");
    expect(body).toEqual([paragraph(text("Huvudstaden är "), gap("gap_002"), text("."))]);
    expect(opened.updates).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("teleports the button to the document body with a fixed position", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const button = gapButton();
    expect(button).not.toBeNull();
    expect(button?.parentElement).toBe(document.body);
    expect(button?.classList.contains("fixed")).toBe(true);
  });

  it("hides on window scroll and removes the scroll listener", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 60, right: 90, bottom: 74 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).not.toBeNull();

    const removeSpy = vi.spyOn(window, "removeEventListener");
    window.dispatchEvent(new Event("scroll"));
    await nextTick();
    expect(gapButton()).toBeNull();
    expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
  });
});
