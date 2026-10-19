/**
 * Exam workspace rich-text editor: the floating gap button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 Q12):
 *   A click inside a word shows a small glyph-only floating button right
 *   after that word, on the word's own line ("Gör till lucka" tooltip and
 *   accessible name only, no border, fill or shadow); one click on it converts
 *   the word. The button stays while later
 *   transactions leave the document and the caret inside the word, and hides
 *   on any document change, on a caret move out of the word, on scroll or
 *   resize, on Escape, and when the editor is disabled or has no next gap id.
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
import { ANCHORED_EDGE_PX, ANCHORED_GAP_PX } from "./useExamWorkspaceAnchoredPosition";
import { wordRangeAtDocPosition } from "./examWorkspaceGapWord";

/**
 * jsdom has no layout: `coordsAtPos` returns one fixed line box for every
 * position, and the floating button's `offsetHeight`/`offsetWidth` are 0.
 * The placement under test is therefore `left = box.right +
 * ANCHORED_GAP_PX` (clamped to the viewport) and `top = box.top +
 * (boxHeight - 0) / 2`, which keeps the button on the word's own line.
 */
const LINE_BOX = { left: 50, top: 60, right: 90, bottom: 74 };

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
    stubGeometry(opened, LINE_BOX);
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

  it("sits right after the clicked word on that word's line", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, LINE_BOX);
    const clickPos = posIn(opened.editor, "Paris", 1);
    const word = wordRangeAtDocPosition(opened.editor.state.doc, clickPos);
    opened.editor.commands.setTextSelection(clickPos);
    clickAt(opened, clickPos);
    await nextTick();
    await nextTick();

    const calls = vi.mocked(opened.editor.view.coordsAtPos).mock.calls;
    expect(calls.some(([pos, side]) => pos === word?.to && side === -1)).toBe(true);
    const button = shownGapButton();
    expect(button.style.left).toBe(`${LINE_BOX.right + ANCHORED_GAP_PX}px`);
    const top = Number.parseFloat(button.style.top);
    expect(top).toBe(LINE_BOX.top + (LINE_BOX.bottom - LINE_BOX.top) / 2);
    expect(top).toBeGreaterThanOrEqual(LINE_BOX.top);
    expect(top).toBeLessThanOrEqual(LINE_BOX.bottom);
  });

  it("stays on the word's line with left clamped at the right viewport edge", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, LINE_BOX);
    vi.spyOn(window, "innerWidth", "get").mockReturnValue(LINE_BOX.right + ANCHORED_GAP_PX + 2);
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const button = shownGapButton();
    const maxLeft = LINE_BOX.right + ANCHORED_GAP_PX + 2 - ANCHORED_EDGE_PX;
    expect(button.style.left).toBe(`${maxLeft}px`);
    const top = Number.parseFloat(button.style.top);
    expect(top).toBeGreaterThanOrEqual(LINE_BOX.top);
    expect(top).toBeLessThanOrEqual(LINE_BOX.bottom);
  });

  it("shows right after the clicked word and converts it on click", async () => {
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
    expect(button?.textContent?.trim()).toBe("");
    expect(button?.getAttribute("aria-label")).toBe("Gör till lucka");
    expect(button?.getAttribute("title")).toBe("Gör till lucka");
    expect(button?.style.left).toBe("94px");
    expect(button?.style.top).toBe("67px");

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

  it("stays on the word's line when there is no room above it", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    stubGeometry(opened, { left: 50, top: 10, right: 90, bottom: 24 });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    const top = Number.parseFloat(gapButton()?.style.top ?? "");
    expect(top).toBe(10 + (24 - 10) / 2);
    expect(top).toBeGreaterThanOrEqual(10);
    expect(top).toBeLessThanOrEqual(24);
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
