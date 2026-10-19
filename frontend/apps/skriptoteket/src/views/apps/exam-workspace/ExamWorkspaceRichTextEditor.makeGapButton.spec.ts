/**
 * Exam workspace rich-text editor: the floating gap button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   A click inside a word shows a small floating "Lucka" button above that
 *   word ("Gör till lucka" tooltip and accessible name); one click on it converts
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

describe("ExamWorkspaceRichTextEditor makeGap floating button", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseOpenedEditors();
    releaseEditor();
  });

  it("shows above the clicked word and converts it on click", async () => {
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
    expect(button?.textContent).toContain("Lucka");
    expect(button?.textContent).not.toContain("Gör till lucka");
    expect(button?.getAttribute("aria-label")).toBe("Gör till lucka");
    expect(button?.getAttribute("title")).toBe("Gör till lucka");
    expect(button?.style.left).toBe("50px");
    expect(button?.style.top).toBe("56px");

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

  it("places the button below the word when there is no room above it", async () => {
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

    expect(gapButton()?.style.top).toBe("28px");
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
