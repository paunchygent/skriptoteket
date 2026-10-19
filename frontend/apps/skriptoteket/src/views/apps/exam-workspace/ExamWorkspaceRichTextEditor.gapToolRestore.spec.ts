/**
 * Exam workspace rich-text editor: the first gap-tool click on a kept word.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 item 3, unit R3):
 *   With the gap tool on, the first click on a word carrying a kept link
 *   restores the whole gap at once, whether or not the editor had focus and
 *   wherever the selection was before; a double click restores once only.
 *
 * jsdom has no layout and never routes a real DOM press to ProseMirror's
 * click handling on its own, so these specs stub both directions of the
 * pointer geometry (`coordsAtPos` and `posAtCoords`) and dispatch real
 * `mousedown`/`mouseup` pairs on the surface. That runs ProseMirror's own
 * single/double click classification exactly as a real browser does: two
 * presses within 500 ms and 10 px classify the second as a double click,
 * which never reaches `handleClick`.
 *
 * Relationships:
 *   - Mounts through `ExamWorkspaceRichTextEditor.gapTool.specSupport` and
 *     resolves pointer hits through `examWorkspaceGapToolPointer.specSupport`.
 *   - The single-press restore contract also lives in
 *     `ExamWorkspaceRichTextEditor.gapToolRevert.spec` (prop-level dispatch).
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { NativeExamBodySegment } from "../../../api/examWorkspace";
import {
  gap,
  paragraph,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  closeGapToolEditors,
  openEditor,
} from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  GAP_POINTER_CHAR_PX,
  GAP_POINTER_ORIGIN_PX,
  gapPointerMiddle,
  pressGapToolClick,
  stubLinearGapPointerPositions,
} from "./examWorkspaceGapToolPointer.specSupport";

function keptText(value: string, keptGapId: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: keptGapId };
}

function plainText(value: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: null };
}

/** The tool reads the finished selection on the next tick; wait for it. */
async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
}

/** The middle of the character starting at `charPos` on the linear grid. */
function middleOf(charPos: number): number {
  return GAP_POINTER_ORIGIN_PX + charPos * GAP_POINTER_CHAR_PX + GAP_POINTER_CHAR_PX / 2;
}

describe("ExamWorkspaceRichTextEditor first kept-word click", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  it("restores on the first click in an unfocused editor", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    expect(document.activeElement).not.toBe(opened.surface);
    stubLinearGapPointerPositions(opened.editor);

    pressGapToolClick(opened.editor, opened.surface, middleOf(12), 1);
    await settle();

    expect(opened.restores).toEqual([["gap_003", 0]]);
    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("restores on the first click after clicking elsewhere in the same editor", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    stubLinearGapPointerPositions(opened.editor);

    pressGapToolClick(opened.editor, opened.surface, middleOf(23), 1);
    await settle();
    expect(opened.restores).toHaveLength(0);
    expect(opened.creations).toHaveLength(1);

    pressGapToolClick(opened.editor, opened.surface, middleOf(12), 1);
    await settle();

    expect(opened.restores).toEqual([["gap_003", 0]]);
    expect(opened.creations).toHaveLength(1);
  });

  it("restores once only on a double click", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    stubLinearGapPointerPositions(opened.editor);
    const middle = middleOf(12);

    pressGapToolClick(opened.editor, opened.surface, middle, 1);
    await settle();
    expect(opened.restores).toEqual([["gap_003", 0]]);

    // The owner writes the restored gap back before the second press lands,
    // so the second press hits the new chip instead of the kept word.
    await opened.setProps({
      body: [paragraph(plainText("Hon heter "), gap("gap_003"), plainText(" idag."))],
    });
    pressGapToolClick(opened.editor, opened.surface, middle, 2);
    await settle();

    expect(opened.restores).toHaveLength(1);
    expect(opened.reverts).toHaveLength(0);
    expect(opened.creations).toHaveLength(0);
  });

  it("makes exactly one gap on a fast double click of a plain word", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerPositions(opened.editor);
    const middle = middleOf(8);

    pressGapToolClick(opened.editor, opened.surface, middle, 1);
    await settle();
    expect(opened.creations).toHaveLength(1);

    pressGapToolClick(opened.editor, opened.surface, middle, 2);
    await settle();

    expect(opened.creations).toHaveLength(1);
    expect(opened.reverts).toHaveLength(0);
    expect(opened.restores).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
  });

  it("restores when the kept-word click lands fast on the reverted chip's spot", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello "), gap("gap_001"), text(" world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerPositions(opened.editor);

    pressGapToolClick(opened.editor, opened.surface, gapPointerMiddle(7), 1);
    await settle();
    expect(opened.reverts).toEqual(["gap_001"]);

    await opened.setProps({
      body: [paragraph(text("hello "), keptText("world", "gap_003"), text(" today"))],
    });
    pressGapToolClick(opened.editor, opened.surface, gapPointerMiddle(7) + GAP_POINTER_CHAR_PX / 2, 2);
    await settle();

    expect(opened.restores).toEqual([["gap_003", 0]]);
    expect(opened.creations).toHaveLength(0);
  });
});
