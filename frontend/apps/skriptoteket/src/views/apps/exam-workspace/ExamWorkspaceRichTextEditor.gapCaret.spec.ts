/**
 * Exam workspace rich-text editor: the caret after a tool-made gap.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 walk finding A1, most serious):
 *   Every path that makes a gap (a word click with the tool on, a drag
 *   selection, a keyboard selection through the gap command while the tool
 *   is on, a double click) ends with a collapsed text selection directly
 *   after the new chip, so typing continues after the gap and never replaces
 *   it. The gap's popover rule is unchanged: a tool-made gap opens no
 *   popover. Each case also survives the owner round trip (the emitted body
 *   written back through `body`), then typing "X" inserts text after the
 *   chip with the chip still present.
 *
 * jsdom has no layout, so selections are set through TipTap commands, word
 * clicks reach the view through `someProp("handleClick")` with the stubbed
 * linear character grid, a drag release is a real `mouseup` on the surface,
 * and a double click dispatches two press details plus a real `dblclick`,
 * as in `ExamWorkspaceRichTextEditor.gapToolSelection.spec`. The keyboard
 * case drives the gap command the tool's Enter will call (the Enter binding
 * itself is TASK-SKRIPT-40-04-13 H4); typing is `insertContent`, because the
 * browser — not ProseMirror — inserts a typed character.
 */

import { TextSelection } from "@tiptap/pm/state";
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
  targetOf,
} from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";
import {
  gapPointerMiddle,
  stubLinearGapPointerGeometry,
} from "./examWorkspaceGapToolPointer.specSupport";

describe("ExamWorkspaceRichTextEditor gap caret", () => {
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

  /** The selection is a caret directly after the one gap chip. */
  function expectCaretAfterGap(opened: Opened): void {
    const selection = opened.editor.state.selection;
    expect(selection).toBeInstanceOf(TextSelection);
    expect(selection.empty).toBe(true);
    expect(selection.from).toBe(atomPos(opened.editor, "examGap") + 1);
  }

  /**
   * The owner round trip keeps the caret, and typing inserts after the chip:
   * the emitted body written back changes nothing, then "X" lands after the
   * gap while the gap stays. A NodeSelection on the chip would fail here,
   * because typing would replace the chip.
   */
  async function expectOwnerEchoThenTyping(opened: Opened): Promise<void> {
    const [emitted] = opened.creations[0]!;
    await opened.setProps({ body: emitted });
    expectCaretAfterGap(opened);

    opened.editor.commands.insertContent("X");
    await nextTick();

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(1);
    expect(atomPos(opened.editor, "examGap")).toBeGreaterThanOrEqual(0);
    expect(opened.editor.getText()).toContain("X");
    const afterTyping = opened.editor.state.selection;
    expect(afterTyping).toBeInstanceOf(TextSelection);
    expect(afterTyping.empty).toBe(true);
    expect(afterTyping.from).toBe(atomPos(opened.editor, "examGap") + 2);
  }

  it("ends a word click with a caret after the chip, surviving the owner echo and typing", async () => {
    const opened = await openEditor({
      body: [paragraph(text("hello world"))],
      gapsInteractive: true,
      nextGapId: "gap_002",
      gapTool: true,
    });
    stubLinearGapPointerGeometry(opened.editor);
    const caret = posIn(opened.editor, "world", 1);
    opened.editor.commands.setTextSelection(caret);
    pressMouse(opened, "mouseup", 0);
    const handled = clickAt(opened, caret, gapPointerMiddle(caret));
    await settle();

    expect(handled).toBe(true);
    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations[0]![2]).toBe("world");
    expect(opened.creations[0]![0]).toEqual([paragraph(text("hello "), gap("gap_002"))]);
    expect(gapButton()).toBeNull();
    expectCaretAfterGap(opened);

    await expectOwnerEchoThenTyping(opened);
  });

  it("ends a drag over two words with a caret after the chip, surviving the owner echo and typing", async () => {
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
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations[0]![2]).toBe("two words");
    expect(opened.creations[0]![0]).toEqual([paragraph(text("eat "), gap("gap_002"), text(" daily"))]);
    expect(gapButton()).toBeNull();
    expectCaretAfterGap(opened);

    await expectOwnerEchoThenTyping(opened);
  });

  it("ends a keyboard selection through the gap command with a caret after the chip", async () => {
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

    targetOf(opened).makeGap("gap_002");

    expect(opened.creations).toHaveLength(1);
    expect(opened.updates).toHaveLength(0);
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations[0]![2]).toBe("two words");
    expectCaretAfterGap(opened);

    await expectOwnerEchoThenTyping(opened);
  });

  it("ends a double click with one gap and a caret after the chip", async () => {
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
    expect(opened.activations).toHaveLength(0);
    expect(opened.creations[0]![2]).toBe("world");
    expect(gapButton()).toBeNull();
    expectCaretAfterGap(opened);

    await expectOwnerEchoThenTyping(opened);
  });
});
