/**
 * Exam workspace rich-text editor: the gap tool selection and click edge cases.
 *
 * Domain purpose:
 *   Prove how the gap tool turns a highlighted span in one paragraph into one
 *   gap, and that it never makes an empty gap: a two-word drag, a whole
 *   punctuated sentence, a selection across a bold boundary, a spaced
 *   selection, a two-paragraph selection, a selection over a gap chip, a
 *   keyboard selection, a double click, and clicks on a chip's edges. These
 *   cases are expected to pass today; any failure is a defect, not a scope
 *   for production change.
 *
 * Relationships:
 *   - Mounts through `ExamWorkspaceRichTextEditor.gapTool.specSupport` and
 *     resolves pointer hits through the stubbed linear character grid in
 *     `examWorkspaceGapToolPointer.specSupport`, as
 *     `ExamWorkspaceRichTextEditor.gapTool.spec` does.
 *   - Covers the selection half of TASK-SKRIPT-40-04-09 Q6; word clicks live
 *     in `ExamWorkspaceRichTextEditor.gapTool.spec`.
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
import type { Opened } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  clickAt,
  closeGapToolEditors,
  gapButton,
  openEditor,
  pressMouse,
  releaseMouse,
  targetOf,
} from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";

describe("ExamWorkspaceRichTextEditor gap tool selection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  /** The tool reads the finished selection on the next tick; wait for it. */
  async function settle(): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
  }

  /** A click with a real button detail, as a first or second press of a double click. */
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

  /** No `createGap` anywhere in this editor ever carries an empty or whitespace seed. */
  function expectNoEmptySeeds(opened: Opened): void {
    for (const [, , seed] of opened.creations) {
      expect(seed.trim()).not.toBe("");
    }
  }

  it("turns a two-word drag in one paragraph into one gap, with no update", async () => {
    const opened = await openEditor({
      body: [paragraph(text("eat two words daily"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    pressMouse(opened, "mousedown", 0);
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "two words", 0),
      to: posIn(opened.editor, "two words", 9),
    });
    pressMouse(opened, "mouseup", 0);
    await settle();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("two words");
    expect(body).toEqual([paragraph(text("eat "), gap("gap_002"), text(" daily"))]);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });

  it("turns a whole punctuated sentence into one gap with the period in the seed", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Hon heter Anna, och hon bor i Lund."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "Hon heter", 0),
      to: posIn(opened.editor, "bor i Lund.", 11),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("Hon heter Anna, och hon bor i Lund.");
    expect(body).toEqual([paragraph(gap("gap_002"))]);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });

  it("turns a selection across a bold boundary into one gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("ab"), text("cd", ["bold"]), text(" ef"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "ab", 0),
      to: posIn(opened.editor, " ef", 3),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("abcd ef");
    expect(body).toEqual([paragraph(gap("gap_002"))]);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });

  it("trims the seed but replaces the whole spaced selection", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a two words b"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "a two", 1),
      to: posIn(opened.editor, "words b", 6),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("two words");
    expect(body).toEqual([paragraph(text("a"), gap("gap_002"), text("b"))]);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });

  it("leaves a selection across two paragraphs unchanged on release", async () => {
    const opened = await openEditor({
      body: [paragraph(text("first")), paragraph(text("second"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const from = posIn(opened.editor, "first", 2);
    const to = posIn(opened.editor, "second", 3);
    opened.editor.commands.setTextSelection({ from, to });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("first\n\nsecond");
    expect(opened.editor.state.selection.from).toBe(from);
    expect(opened.editor.state.selection.to).toBe(to);
    expectNoEmptySeeds(opened);
  });

  it("leaves a selection containing a gap chip unchanged on release", async () => {
    const opened = await openEditor({
      body: [paragraph(text("a"), gap("gap_001"), text("b"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    const before = JSON.stringify(opened.editor.getJSON());
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "a", 0),
      to: posIn(opened.editor, "b", 1),
    });
    await releaseMouse(opened);

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(JSON.stringify(opened.editor.getJSON())).toBe(before);
    expect(opened.editor.getText()).toBe("ab");
    expectNoEmptySeeds(opened);
  });

  it("ignores a keyboard selection until the Lucka control converts it", async () => {
    const opened = await openEditor({
      body: [paragraph(text("eat two words daily"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    opened.editor.commands.setTextSelection({
      from: posIn(opened.editor, "two words", 0),
      to: posIn(opened.editor, "two words", 9),
    });
    await settle();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("eat two words daily");

    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("two words");
    expect(body).toEqual([paragraph(text("eat "), gap("gap_002"), text(" daily"))]);
    expectNoEmptySeeds(opened);
  });

  it("makes exactly one gap on a double click, with no empty gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "world", 1);
    const middle = gapPointerMiddle(caret);
    opened.editor.commands.setTextSelection(caret);

    pressMouse(opened, "mousedown", 0);
    pressMouse(opened, "mouseup", 0);
    // jsdom never routes a real DOM click to ProseMirror's `handleClick`
    // without layout, so each press dispatches through the prop, as the
    // other gap tool click specs do; the `dblclick` below is a real DOM
    // event, which the editor ignores.
    clickWithDetail(opened, caret, middle, 1);
    await settle();
    pressMouse(opened, "mousedown", 0);
    pressMouse(opened, "mouseup", 0);
    clickWithDetail(opened, caret, middle, 2);
    await settle();
    opened.surface.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, clientX: middle }));
    await settle();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("world");
    expect(body).toEqual([paragraph(text("hello "), gap("gap_002"))]);
    // The second press runs only the `handleClick` path here, which never
    // routes to `handleClickOn`; a tap on the new chip would open it through
    // `handleClickOn`, as the chip click spec in `gapTool.spec` proves.
    expect(opened.activations).toHaveLength(0);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });

  it("never gaps or removes a chip on edge and after-chip clicks", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello "), gap("gap_001"), text(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const chip = atomPos(opened.editor, "examGap");
    const before = JSON.stringify(opened.editor.getJSON());

    expect(clickAt(opened, chip, gapPointerMiddle(chip))).toBeFalsy();
    await nextTick();
    expect(clickAt(opened, chip + 1, gapPointerMiddle(chip))).toBeFalsy();
    await nextTick();
    opened.editor.commands.setTextSelection(chip + 1);
    expect(clickAt(opened, chip + 1, gapPointerMiddle(chip + 1))).toBeFalsy();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.activations).toHaveLength(0);
    expect(JSON.stringify(opened.editor.getJSON())).toBe(before);
    expect(atomPos(opened.editor, "examGap")).toBe(chip);
    expect(gapButton()).toBeNull();
    expectNoEmptySeeds(opened);
  });
});
