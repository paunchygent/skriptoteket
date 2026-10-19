/**
 * Exam workspace rich-text editor: the gap tool pointer and selection conversion.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 G1):
 *   With the `gapTool` prop on, a primary click inside a word turns that word
 *   into a gap at once (one `createGap`, never `update`, no floating button),
 *   and a drag selection inside one paragraph turns into one gap on mouseup.
 *   A click on a space only places the caret, a click on a gap chip still
 *   opens it (`activateGap`), typing still emits `update`, and with the prop
 *   off a word click only places the caret and never shows a button.
 *
 * jsdom has no layout, so selections are set through TipTap commands, clicks
 * reach the view through `someProp("handleClick")`, a drag release is a real
 * `mouseup` event on the surface (the tool reads the finished selection on
 * the next tick), and character boxes are stubbed as fixed 10px columns so
 * pointer hits can be told apart from caret positions. A primary drag is a
 * real `mousedown` button 0 followed by `mouseup` button 0; any other button
 * or a release with no press in this editor converts nothing.
 * The button teleports to document.body, so it is found through `document`.
 * Shared mount helpers live in `ExamWorkspaceRichTextEditor.gapTool.specSupport`;
 * shortcut and Escape wiring live in `ExamWorkspaceRichTextEditor.gapToolWiring.spec`.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import {
  atomPos,
  gap,
  paragraph,
  posIn,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  clickAt,
  closeGapToolEditors,
  gapButton,
  openEditor,
  pressMouse,
  releaseMouse
} from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  gapPointerMiddle,
  gapPointerMiddleDecreasing,
  stubDecreasingGapPointerGeometry,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";

describe("ExamWorkspaceRichTextEditor gap tool", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  it("turns the clicked word into a gap at once, with no floating button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "world", 1);
    opened.editor.commands.setTextSelection(caret);
    // The browser's mouseup runs before the click; the deferred release check
    // must not add a second gap after the click already converted the word.
    pressMouse(opened, "mouseup", 0);
    const handled = clickAt(opened, caret, gapPointerMiddle(caret));
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
    stubLinearGapPointerGeometry(opened.editor);
    const space = posIn(opened.editor, "hello world ", 11);
    const end = posIn(opened.editor, "hello world ", 12);
    opened.editor.commands.setTextSelection(end);
    const handled = clickAt(opened, end, gapPointerMiddle(space));
    await nextTick();

    expect(handled).toBeFalsy();
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("hello world ");
    expect(gapButton()).toBeNull();
  });

  it("makes no gap on a click on the space between two words, from either edge", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Solen är"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const space = posIn(opened.editor, "Solen är", 5);
    opened.editor.commands.setTextSelection(space);

    expect(clickAt(opened, space, gapPointerMiddle(space))).toBeFalsy();
    expect(clickAt(opened, space + 1, gapPointerMiddle(space))).toBeFalsy();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("Solen är");
    expect(gapButton()).toBeNull();
  });

  it("turns a clicked Hebrew word into a gap when columns decrease left", async () => {
    const opened = await openEditor({
      body: [paragraph(text("שלום עולם"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubDecreasingGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "שלום עולם", 1);
    opened.editor.commands.setTextSelection(caret);
    pressMouse(opened, "mouseup", 0);
    const handled = clickAt(opened, caret, gapPointerMiddleDecreasing(caret));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(handled).toBe(true);
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("שלום");
    expect(body).toEqual([paragraph(gap("gap_002"), text(" עולם"))]);
    expect(gapButton()).toBeNull();
  });

  it("makes no gap on a click on the space between two Hebrew words", async () => {
    const opened = await openEditor({
      body: [paragraph(text("שלום עולם"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubDecreasingGapPointerGeometry(opened.editor);
    const space = posIn(opened.editor, "שלום עולם", 4);
    opened.editor.commands.setTextSelection(space);

    expect(clickAt(opened, space, gapPointerMiddleDecreasing(space))).toBeFalsy();
    expect(clickAt(opened, space + 1, gapPointerMiddleDecreasing(space))).toBeFalsy();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("שלום עולם");
    expect(gapButton()).toBeNull();
  });

  it("makes no gap on a click on the period after a word", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const period = posIn(opened.editor, "Paris.", 5);
    opened.editor.commands.setTextSelection(period);

    expect(clickAt(opened, period, gapPointerMiddle(period))).toBeFalsy();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("Huvudstaden är Paris.");
    expect(gapButton()).toBeNull();
  });

  it("makes no gap when a right-click releases over an existing selection", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    pressMouse(opened, "mousedown", 2);
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "hello world", 0),
      to: posIn(opened.editor, "hello world", 5),
    });
    pressMouse(opened, "mouseup", 2);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(opened.editor.state.selection.empty).toBe(false);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("hello world");
  });

  it("makes no gap on a primary release with no press in this editor", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "hello world", 0),
      to: posIn(opened.editor, "hello world", 5),
    });
    pressMouse(opened, "mouseup", 0);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("hello world");
  });

  it("still gaps a primary drag selection on release", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    pressMouse(opened, "mousedown", 0);
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "hello world", 6),
      to: posIn(opened.editor, "hello world", 11),
    });
    pressMouse(opened, "mouseup", 0);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("world");
    expect(body).toEqual([paragraph(text("hello "), gap("gap_002"))]);
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

  it("with the tool off, a word click creates no gap and shows no button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    const handled = clickAt(opened, posIn(opened.editor, "world", 1));
    await nextTick();
    await nextTick();

    expect(handled).toBeFalsy();
    expect(opened.creations).toHaveLength(0);
    expect(gapButton()).toBeNull();
  });

  it("with the tool off, turning the tool on still creates nothing by itself", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "world", 1));
    clickAt(opened, posIn(opened.editor, "world", 1));
    await nextTick();
    await nextTick();
    expect(gapButton()).toBeNull();

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
