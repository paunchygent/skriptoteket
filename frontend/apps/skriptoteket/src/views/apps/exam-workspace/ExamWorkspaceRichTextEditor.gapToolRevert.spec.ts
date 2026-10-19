/**
 * Exam workspace rich-text editor: the gap tool revert and restore clicks.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 items 1, 3, 4, 6-8, unit H4):
 *   With the tool on, a click on a gap chip emits `revertGap` instead of
 *   opening its popover; with the tool off the chip still emits
 *   `activateGap`. With the tool on, a click on a word carrying a kept link
 *   emits `restoreKeptGap` with the kept id and the clicked block's index,
 *   never a `createGap`. The second click of a double click does nothing: a
 *   word click with detail 2 creates no gap, and a chip click with detail 2
 *   neither reverts nor opens. With the tool on, Enter or Space on a selected
 *   gap emits `activateGap`, and Enter on a non-empty keyboard selection
 *   emits one `createGap` through the same path as a drag selection.
 *
 * jsdom has no layout, so selections are set through TipTap commands, clicks
 * reach the view through its own click handlers, and keys are real `keydown`
 * events on the surface, as the other gap tool specs do.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { NativeExamBodySegment } from "../../../api/examWorkspace";
import {
  atomPos,
  gap,
  paragraph,
  posIn,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import type { Opened } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  clickAt,
  closeGapToolEditors,
  openEditor,
  pressMouse,
} from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";

function keptText(value: string, keptGapId: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: keptGapId };
}

function plainText(value: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: null };
}

/** A primary click carrying the given click count, as the browser sends it. */
function clickWithDetail(opened: Opened, pos: number, clientX: number, detail: number): unknown {
  let result: unknown;
  opened.editor.view.someProp("handleClick", (handler) => {
    result = handler(
      opened.editor.view,
      pos,
      new MouseEvent("click", { bubbles: true, cancelable: true, clientX, detail }),
    );
    return result;
  });
  return result;
}

/** A click on a gap chip carrying the given click count. */
function clickChipWithDetail(opened: Opened, gapId: string, detail: number): unknown {
  let found = -1;
  opened.editor.state.doc.descendants((node, nodePos) => {
    if (found < 0 && node.type.name === "examGap" && node.attrs.gapId === gapId) {
      found = nodePos;
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no gap ${gapId}`);
  }
  const node = opened.editor.state.doc.nodeAt(found);
  if (!node) {
    throw new Error(`no gap ${gapId}`);
  }
  let result: unknown;
  opened.editor.view.someProp("handleClickOn", (handler) => {
    result = handler(
      opened.editor.view,
      found,
      node,
      found,
      new MouseEvent("click", { bubbles: true, cancelable: true, detail }),
      true,
    );
    return result;
  });
  return result;
}

function pressKey(surface: HTMLElement, key: string, keyCode: number): void {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  Object.defineProperty(event, "keyCode", { value: keyCode });
  Object.defineProperty(event, "which", { value: keyCode });
  surface.dispatchEvent(event);
}

describe("ExamWorkspaceRichTextEditor gap tool revert and restore", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  it("with the tool on, a gap click emits revertGap instead of opening the popover", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("hello "), gap("gap_001"), plainText(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const gapPos = atomPos(opened.editor, "examGap");
    const node = opened.editor.state.doc.nodeAt(gapPos);
    const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
      handler(
        opened.editor.view,
        gapPos,
        node!,
        gapPos,
        new MouseEvent("click", { bubbles: true, cancelable: true, detail: 1 }),
        true,
      ),
    );

    expect(handled).toBe(true);
    expect(opened.reverts).toEqual(["gap_001"]);
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("with the tool off, a gap click still opens the popover", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("hello "), gap("gap_001"), plainText(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    const gapPos = atomPos(opened.editor, "examGap");
    const node = opened.editor.state.doc.nodeAt(gapPos);
    const handled = opened.editor.view.someProp("handleClickOn", (handler) =>
      handler(
        opened.editor.view,
        gapPos,
        node!,
        gapPos,
        new MouseEvent("click", { bubbles: true, cancelable: true, detail: 1 }),
        true,
      ),
    );

    expect(handled).toBe(true);
    expect(opened.activations).toHaveLength(1);
    expect(opened.activations[0]![0]).toBe("gap_001");
    expect(opened.reverts).toHaveLength(0);
    expect(opened.creations).toHaveLength(0);
  });

  it("with the tool on, a kept-word click emits restoreKeptGap and makes no gap", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "Stockholm", 1);
    opened.editor.commands.setTextSelection(caret);
    pressMouse(opened, "mouseup", 0);
    const handled = clickAt(opened, caret, gapPointerMiddle(caret));
    await nextTick();

    expect(handled).toBe(true);
    expect(opened.restores).toEqual([["gap_003", 0]]);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.activations).toHaveLength(0);
  });

  it("with the tool on, a click on the second block of a split kept id restores that block", async () => {
    const opened = await openEditor({
      body: [
        paragraph(
          plainText("Hon heter "),
          keptText("ett", "gap_003"),
          plainText(" och "),
          gap("gap_002"),
          plainText(" plus "),
          keptText("två", "gap_003"),
          plainText(" ."),
        ),
      ],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "två", 1);
    opened.editor.commands.setTextSelection(caret);
    pressMouse(opened, "mouseup", 0);
    const handled = clickAt(opened, caret, gapPointerMiddle(caret));
    await nextTick();

    expect(handled).toBe(true);
    expect(opened.restores).toEqual([["gap_003", 1]]);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("with the tool off, a kept-word click only places the caret", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "Stockholm", 1);
    opened.editor.commands.setTextSelection(caret);
    const handled = clickAt(opened, caret, gapPointerMiddle(caret));
    await nextTick();

    expect(opened.restores).toHaveLength(0);
    expect(opened.creations).toHaveLength(0);
    expect(handled).toBeFalsy();
  });

  it("the second click of a double click on a word creates no second gap", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "world", 1);
    opened.editor.commands.setTextSelection(caret);
    pressMouse(opened, "mouseup", 0);

    expect(clickWithDetail(opened, caret, gapPointerMiddle(caret), 1)).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    expect(clickWithDetail(opened, caret, gapPointerMiddle(caret), 2)).toBeFalsy();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    expect(opened.reverts).toHaveLength(0);
  });

  it("the second click of a double click on a gap neither reverts nor opens it", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("hello "), gap("gap_001"), plainText(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });

    expect(clickChipWithDetail(opened, "gap_001", 2)).toBeFalsy();

    expect(opened.reverts).toHaveLength(0);
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("with the tool on, Enter and Space on a selected gap open its popover", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("hello "), gap("gap_001"), plainText(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const chip = atomPos(opened.editor, "examGap");
    opened.editor.commands.setNodeSelection(chip);

    pressKey(opened.surface, "Enter", 13);
    expect(opened.activations).toHaveLength(1);
    expect(opened.activations[0]![0]).toBe("gap_001");

    opened.editor.commands.setNodeSelection(chip);
    pressKey(opened.surface, " ", 32);
    expect(opened.activations).toHaveLength(2);
    expect(opened.activations[1]![0]).toBe("gap_001");
    expect(opened.creations).toHaveLength(0);
  });

  it("with the tool on, Enter on a non-empty keyboard selection makes it a gap", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("eat two words daily"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "two words", 0),
      to: posIn(opened.editor, "two words", 9),
    });

    pressKey(opened.surface, "Enter", 13);
    await nextTick();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("two words");
    expect(body).toEqual([paragraph(text("eat "), gap("gap_002"), text(" daily"))]);
  });

  it("with the tool off, Enter on a selection makes no gap", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("eat two words daily"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "two words", 0),
      to: posIn(opened.editor, "two words", 9),
    });

    pressKey(opened.surface, "Enter", 13);
    await nextTick();

    expect(opened.creations).toHaveLength(0);
  });
});
