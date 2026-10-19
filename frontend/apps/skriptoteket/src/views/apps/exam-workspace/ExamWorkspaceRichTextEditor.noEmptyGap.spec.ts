/**
 * Exam workspace rich-text editor: only Tom lucka inserts an empty gap.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviours 8 and 9):
 *   With the gap tool off and on, no toolbar button and no click outside
 *   a word creates a gap chip: the only empty-gap path is Tom lucka
 *   (`insertEmptyGapAtCursor`, covered in
 *   `ExamWorkspaceRichTextEditor.emptyGap.spec.ts`). A tool-off click only
 *   places the caret and never shows the floating "Gör till lucka" button; a
 *   tool-on click on a separator only places the caret. The word under the
 *   pointer still becomes one seeded gap with the tool on, so the tool stays
 *   the one gap control for existing text.
 *
 * jsdom has no layout, so selections are set through TipTap commands,
 * clicks reach the view through `someProp("handleClick")`, and pointer
 * hits resolve through the stubbed linear character grid in
 * `examWorkspaceGapToolPointer.specSupport`.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import {
  gap,
  paragraph,
  posIn,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";
import {
  clickAt,
  gapButton,
  openEditor,
  releaseMakeGapEditors,
} from "./ExamWorkspaceRichTextEditor.makeGap.specSupport";
import {
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";

describe("ExamWorkspaceRichTextEditor no empty gap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    releaseMakeGapEditors();
  });

  it("with the tool off, a click inside a word creates no gap and shows no button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "Paris", 1));
    clickAt(opened, posIn(opened.editor, "Paris", 1));
    await nextTick();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("Huvudstaden är Paris.");
    expect(gapButton()).toBeNull();
  });

  it("with the tool off, a click on a space creates no gap and shows no button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Huvudstaden är Paris."))],
      gapsInteractive: true,
      nextGapId: "gap_002",
    });
    const space = posIn(opened.editor, "Huvudstaden är Paris.", 11);
    opened.editor.commands.setTextSelection(space);
    clickAt(opened, space);
    await nextTick();
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("Huvudstaden är Paris.");
    expect(gapButton()).toBeNull();
  });

  it("with the tool on, a click on the space between two words creates no gap", async () => {
    const opened = await openEditor({
      body: [paragraph(text("Solen är"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const space = posIn(opened.editor, "Solen är", 5);
    opened.editor.commands.setTextSelection(space);
    clickAt(opened, space, gapPointerMiddle(space));
    await nextTick();

    expect(opened.creations).toHaveLength(0);
    expect(opened.updates).toHaveLength(0);
    expect(opened.editor.getText()).toBe("Solen är");
    expect(gapButton()).toBeNull();
  });

  it("with the tool on, a click inside a word still makes one seeded gap with no button", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "world", 1);
    opened.editor.commands.setTextSelection(caret);
    clickAt(opened, caret, gapPointerMiddle(caret));
    await nextTick();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    const [body, gapId, seed] = opened.creations[0]!;
    expect(gapId).toBe("gap_002");
    expect(seed).toBe("world");
    expect(body).toEqual([paragraph(text("hello "), gap("gap_002"))]);
    expect(gapButton()).toBeNull();
  });
});
